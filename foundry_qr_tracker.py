#!/usr/bin/env python3
"""
Foundry VTT QR Code Token Tracker
=================================

A Python script that uses the Raspberry Pi camera to track QR code tokens
and sends real-time position updates to Foundry Virtual Tabletop.

Requirements:
- Raspberry Pi with camera module
- Python packages: picamera2, opencv-python, pyzbar, numpy, websockets, requests
- Foundry VTT with compatible module (see README)

Installation:
sudo apt update
sudo apt install python3-opencv python3-numpy
pip3 install picamera2 pyzbar websockets requests aiohttp

Usage:
python3 foundry_qr_tracker.py --foundry-url "http://localhost:30000" --scene-id "your-scene-id"
"""

import cv2
import numpy as np
from picamera2 import Picamera2
from pyzbar import pyzbar
import time
import json
import asyncio
import websockets
import requests
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional, Callable
import threading
import queue
import logging
from pathlib import Path


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QRToken:
    """Represents a detected QR code token."""
    id: str
    x: float
    y: float
    confidence: float
    last_seen: float
    corners: List[Tuple[int, int]]
    foundry_token_id: Optional[str] = None


@dataclass
class FoundryConfig:
    """Configuration for Foundry VTT integration."""
    base_url: str
    scene_id: str
    api_key: Optional[str] = None
    websocket_port: int = 30001
    grid_size: int = 100  # Foundry grid size in pixels
    scene_width: int = 4000  # Scene width in pixels
    scene_height: int = 3000  # Scene height in pixels


class FoundryIntegrator:
    """Handles integration with Foundry VTT."""
    
    def __init__(self, config: FoundryConfig):
        self.config = config
        self.session = requests.Session()
        self.websocket = None
        self.token_mapping = {}  # QR ID -> Foundry Token ID
        self.connection_active = False
        
        # Set up authentication if API key provided
        if config.api_key:
            self.session.headers.update({
                'Authorization': f'Bearer {config.api_key}'
            })
    
    async def connect_websocket(self):
        """Connect to Foundry via WebSocket for real-time updates."""
        try:
            # Extract host from base_url properly
            from urllib.parse import urlparse
            parsed_url = urlparse(self.config.base_url)
            host = parsed_url.hostname or parsed_url.netloc.split(':')[0]
            
            ws_url = f"ws://{host}:{self.config.websocket_port}"
            logger.info(f"Connecting to Foundry WebSocket: {ws_url}")
            
            # Add timeout and connection options for remote connections
            self.websocket = await websockets.connect(
                ws_url, 
                timeout=10,
                ping_interval=20,
                ping_timeout=10
            )
            self.connection_active = True
            logger.info("Connected to Foundry WebSocket")
            
            # Send initial handshake with network info
            handshake = {
                "type": "handshake",
                "source": "qr_tracker",
                "scene_id": self.config.scene_id,
                "tracker_host": "raspberry_pi",
                "timestamp": time.time()
            }
            await self.websocket.send(json.dumps(handshake))
            
        except Exception as e:
            logger.error(f"Failed to connect to Foundry WebSocket: {e}")
            logger.error(f"Ensure Foundry host {host} is accessible and WebSocket port {self.config.websocket_port} is open")
            self.connection_active = False
    
    async def disconnect_websocket(self):
        """Disconnect from Foundry WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.connection_active = False
            logger.info("Disconnected from Foundry WebSocket")
    
    def surface_to_foundry_coords(self, surface_x: float, surface_y: float, 
                                  surface_width: float, surface_height: float) -> Tuple[int, int]:
        """Convert surface coordinates to Foundry scene coordinates."""
        # Normalize surface coordinates (0-1)
        norm_x = surface_x / surface_width
        norm_y = surface_y / surface_height
        
        # Convert to Foundry scene coordinates
        foundry_x = int(norm_x * self.config.scene_width)
        foundry_y = int(norm_y * self.config.scene_height)
        
        return foundry_x, foundry_y
    
    async def update_token_position_ws(self, qr_token: QRToken, surface_width: float, surface_height: float):
        """Update token position via WebSocket."""
        if not self.connection_active or not self.websocket:
            return False
        
        try:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                qr_token.x, qr_token.y, surface_width, surface_height)
            
            update_message = {
                "type": "token_update",
                "scene_id": self.config.scene_id,
                "qr_id": qr_token.id,
                "token_id": qr_token.foundry_token_id,
                "x": foundry_x,
                "y": foundry_y,
                "confidence": qr_token.confidence
            }
            
            await self.websocket.send(json.dumps(update_message))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {e}")
            return False
    
    def update_token_position_http(self, qr_token: QRToken, surface_width: float, surface_height: float):
        """Update token position via HTTP API."""
        try:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                qr_token.x, qr_token.y, surface_width, surface_height)
            
            # Foundry API endpoint for updating tokens
            url = f"{self.config.base_url}/api/tokens/{qr_token.foundry_token_id}"
            
            payload = {
                "x": foundry_x,
                "y": foundry_y,
                "_id": qr_token.foundry_token_id
            }
            
            response = self.session.patch(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send HTTP update: {e}")
            return False
    
    def create_or_find_token(self, qr_id: str) -> Optional[str]:
        """Create or find a token in Foundry for the QR ID."""
        try:
            # First, try to find existing token
            url = f"{self.config.base_url}/api/scenes/{self.config.scene_id}/tokens"
            response = self.session.get(url)
            
            if response.status_code == 200:
                tokens = response.json()
                for token in tokens:
                    if token.get('name') == f"Player_{qr_id}" or token.get('flags', {}).get('qr_id') == qr_id:
                        logger.info(f"Found existing token for QR {qr_id}: {token['_id']}")
                        return token['_id']
            
            # Create new token if not found
            create_payload = {
                "name": f"Player_{qr_id}",
                "x": 100,
                "y": 100,
                "img": "icons/svg/mystery-man.svg",  # Default token image
                "width": 1,
                "height": 1,
                "flags": {
                    "qr_id": qr_id,
                    "qr_tracker": True
                }
            }
            
            response = self.session.post(url, json=create_payload)
            if response.status_code == 201:
                token_data = response.json()
                logger.info(f"Created new token for QR {qr_id}: {token_data['_id']}")
                return token_data['_id']
            
        except Exception as e:
            logger.error(f"Failed to create/find token for QR {qr_id}: {e}")
        
        return None
    
    def export_to_foundry_module(self, tokens: List[QRToken], surface_width: float, surface_height: float):
        """Export token data to a file that a Foundry module can read."""
        output_data = {
            "timestamp": time.time(),
            "scene_id": self.config.scene_id,
            "tokens": []
        }
        
        for token in tokens:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                token.x, token.y, surface_width, surface_height)
            
            token_data = {
                "qr_id": token.id,
                "foundry_token_id": token.foundry_token_id,
                "x": foundry_x,
                "y": foundry_y,
                "confidence": token.confidence,
                "last_seen": token.last_seen
            }
            output_data["tokens"].append(token_data)
        
        # Write to file that Foundry module can monitor
        output_path = Path("foundry_token_data.json")
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)


class SurfaceCalibrator:
    """Handles calibration of the surface area for coordinate mapping."""
    
    def __init__(self):
        self.surface_corners = None
        self.transform_matrix = None
        self.surface_width = 1000
        self.surface_height = 1000
    
    def calibrate_surface(self, frame: np.ndarray) -> bool:
        """Calibrate the surface by detecting corner markers or manual selection."""
        print("Surface calibration mode:")
        print("1. Place 4 corner markers (QR codes with 'CORNER_TL', 'CORNER_TR', 'CORNER_BL', 'CORNER_BR')")
        print("2. Or press 'c' to manually select corners")
        
        if self._detect_corner_markers(frame):
            return True
        
        return self._manual_corner_selection(frame)
    
    def _detect_corner_markers(self, frame: np.ndarray) -> bool:
        """Detect corner markers automatically."""
        qr_codes = pyzbar.decode(frame)
        corners = {}
        
        for qr in qr_codes:
            data = qr.data.decode('utf-8')
            if data in ['CORNER_TL', 'CORNER_TR', 'CORNER_BL', 'CORNER_BR']:
                points = qr.polygon
                if len(points) == 4:
                    center_x = sum(p.x for p in points) // len(points)
                    center_y = sum(p.y for p in points) // len(points)
                    corners[data] = (center_x, center_y)
        
        if len(corners) == 4:
            self.surface_corners = np.array([
                corners['CORNER_TL'], corners['CORNER_TR'],
                corners['CORNER_BR'], corners['CORNER_BL']
            ], dtype=np.float32)
            self._calculate_transform_matrix()
            print("Surface calibrated using corner markers!")
            return True
        
        return False
    
    def _manual_corner_selection(self, frame: np.ndarray) -> bool:
        """Manual corner selection interface."""
        corners = []
        corner_names = ["Top-Left", "Top-Right", "Bottom-Right", "Bottom-Left"]
        
        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(corners) < 4:
                corners.append((x, y))
                print(f"Selected {corner_names[len(corners)-1]} corner: ({x}, {y})")
        
        cv2.namedWindow("Calibration - Click 4 corners")
        cv2.setMouseCallback("Calibration - Click 4 corners", mouse_callback)
        
        while len(corners) < 4:
            display_frame = frame.copy()
            
            for i, corner in enumerate(corners):
                cv2.circle(display_frame, corner, 5, (0, 255, 0), -1)
                cv2.putText(display_frame, corner_names[i], 
                           (corner[0] + 10, corner[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            if len(corners) < 4:
                cv2.putText(display_frame, f"Click {corner_names[len(corners)]} corner",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow("Calibration - Click 4 corners", display_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:
                cv2.destroyAllWindows()
                return False
        
        self.surface_corners = np.array(corners, dtype=np.float32)
        self._calculate_transform_matrix()
        cv2.destroyAllWindows()
        print("Surface calibrated manually!")
        return True
    
    def _calculate_transform_matrix(self):
        """Calculate perspective transform matrix."""
        dst_points = np.array([
            [0, 0], [self.surface_width, 0],
            [self.surface_width, self.surface_height], [0, self.surface_height]
        ], dtype=np.float32)
        
        self.transform_matrix = cv2.getPerspectiveTransform(
            self.surface_corners, dst_points)
    
    def camera_to_surface_coords(self, camera_x: int, camera_y: int) -> Tuple[float, float]:
        """Convert camera coordinates to surface coordinates."""
        if self.transform_matrix is None:
            return float(camera_x), float(camera_y)
        
        point = np.array([[[camera_x, camera_y]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point, self.transform_matrix)
        return float(transformed[0][0][0]), float(transformed[0][0][1])


class FoundryQRTracker:
    """Main QR code tracking system with Foundry VTT integration."""
    
    def __init__(self, foundry_config: FoundryConfig, surface_width: int = 1000, surface_height: int = 1000):
        self.picam = None
        self.calibrator = SurfaceCalibrator()
        self.calibrator.surface_width = surface_width
        self.calibrator.surface_height = surface_height
        
        self.foundry = FoundryIntegrator(foundry_config)
        self.tracked_tokens: Dict[str, QRToken] = {}
        self.token_timeout = 3.0
        self.running = False
        
        # Update settings
        self.update_interval = 0.1  # Send updates every 100ms
        self.last_update_time = 0
    
    def initialize_camera(self) -> bool:
        """Initialize the Raspberry Pi camera."""
        try:
            self.picam = Picamera2()
            config = self.picam.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"}
            )
            self.picam.configure(config)
            self.picam.start()
            time.sleep(2)
            logger.info("Camera initialized successfully!")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            return False
    
    def calibrate(self) -> bool:
        """Calibrate the surface area."""
        if not self.picam:
            logger.error("Camera not initialized!")
            return False
        
        logger.info("Starting surface calibration...")
        frame = self.picam.capture_array()
        return self.calibrator.calibrate_surface(frame)
    
    def detect_qr_codes(self, frame: np.ndarray) -> List[QRToken]:
        """Detect QR codes in the current frame."""
        qr_codes = pyzbar.decode(frame)
        detected_tokens = []
        current_time = time.time()
        
        for qr in qr_codes:
            try:
                qr_data = qr.data.decode('utf-8')
                
                if qr_data.startswith('CORNER_'):
                    continue
                
                points = qr.polygon
                if len(points) >= 4:
                    center_x = sum(p.x for p in points) // len(points)
                    center_y = sum(p.y for p in points) // len(points)
                    
                    surface_x, surface_y = self.calibrator.camera_to_surface_coords(
                        center_x, center_y)
                    
                    qr_area = cv2.contourArea(np.array([(p.x, p.y) for p in points]))
                    confidence = min(1.0, qr_area / 10000.0)
                    
                    # Get or create Foundry token ID
                    foundry_token_id = None
                    if qr_data in self.tracked_tokens:
                        foundry_token_id = self.tracked_tokens[qr_data].foundry_token_id
                    else:
                        foundry_token_id = self.foundry.create_or_find_token(qr_data)
                    
                    token = QRToken(
                        id=qr_data,
                        x=surface_x,
                        y=surface_y,
                        confidence=confidence,
                        last_seen=current_time,
                        corners=[(p.x, p.y) for p in points],
                        foundry_token_id=foundry_token_id
                    )
                    detected_tokens.append(token)
                    
            except Exception as e:
                logger.error(f"Error processing QR code: {e}")
                continue
        
        return detected_tokens
    
    def update_tracked_tokens(self, detected_tokens: List[QRToken]):
        """Update the tracked tokens list."""
        current_time = time.time()
        
        for token in detected_tokens:
            self.tracked_tokens[token.id] = token
        
        tokens_to_remove = []
        for token_id, token in self.tracked_tokens.items():
            if current_time - token.last_seen > self.token_timeout:
                tokens_to_remove.append(token_id)
        
        for token_id in tokens_to_remove:
            del self.tracked_tokens[token_id]
    
    async def send_foundry_updates(self):
        """Send token updates to Foundry VTT."""
        current_time = time.time()
        
        if current_time - self.last_update_time < self.update_interval:
            return
        
        active_tokens = list(self.tracked_tokens.values())
        
        # Send WebSocket updates
        if self.foundry.connection_active:
            for token in active_tokens:
                if token.foundry_token_id:
                    await self.foundry.update_token_position_ws(
                        token, self.calibrator.surface_width, self.calibrator.surface_height)
        
        # Export for Foundry module
        self.foundry.export_to_foundry_module(
            active_tokens, self.calibrator.surface_width, self.calibrator.surface_height)
        
        self.last_update_time = current_time
    
    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw tracking overlay on the frame."""
        overlay_frame = frame.copy()
        
        if self.calibrator.surface_corners is not None:
            corners = self.calibrator.surface_corners.astype(int)
            cv2.polylines(overlay_frame, [corners], True, (0, 255, 0), 2)
        
        for token in self.tracked_tokens.values():
            if token.corners:
                corners_array = np.array(token.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, (255, 0, 0), 2)
            
            # Draw center and info
            if token.corners:
                center_x = sum(c[0] for c in token.corners) // len(token.corners)
                center_y = sum(c[1] for c in token.corners) // len(token.corners)
                
                cv2.circle(overlay_frame, (center_x, center_y), 5, (0, 0, 255), -1)
                
                # Status indicator
                status_color = (0, 255, 0) if token.foundry_token_id else (0, 0, 255)
                status_text = "✓ FOUNDRY" if token.foundry_token_id else "✗ NO TOKEN"
                
                label = f"{token.id} | {status_text}"
                cv2.putText(overlay_frame, label,
                           (center_x + 10, center_y - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, status_color, 1)
                
                coord_label = f"({token.x:.0f}, {token.y:.0f})"
                cv2.putText(overlay_frame, coord_label,
                           (center_x + 10, center_y + 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        
        # Connection status
        connection_status = "FOUNDRY: CONNECTED" if self.foundry.connection_active else "FOUNDRY: DISCONNECTED"
        status_color = (0, 255, 0) if self.foundry.connection_active else (0, 0, 255)
        cv2.putText(overlay_frame, connection_status, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, status_color, 2)
        
        return overlay_frame
    
    async def run_async(self, display: bool = True):
        """Main async tracking loop."""
        if not self.picam:
            logger.error("Camera not initialized!")
            return
        
        # Connect to Foundry
        await self.foundry.connect_websocket()
        
        self.running = True
        logger.info("Starting Foundry QR tracking... Press 'q' to quit, 'r' to recalibrate")
        
        try:
            while self.running:
                frame = self.picam.capture_array()
                detected_tokens = self.detect_qr_codes(frame)
                self.update_tracked_tokens(detected_tokens)
                
                # Send updates to Foundry
                await self.send_foundry_updates()
                
                if display:
                    overlay_frame = self.draw_overlay(frame)
                    cv2.imshow("Foundry QR Tracker", overlay_frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('r'):
                        logger.info("Recalibrating...")
                        self.calibrate()
                
                await asyncio.sleep(0.05)  # 20 FPS
                
        except KeyboardInterrupt:
            logger.info("Stopping tracker...")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the tracking system."""
        self.running = False
        await self.foundry.disconnect_websocket()
        if self.picam:
            self.picam.stop()
        cv2.destroyAllWindows()
        logger.info("Tracker stopped.")


def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description="Foundry VTT QR Token Tracker")
    parser.add_argument("--foundry-url", required=True, help="Foundry VTT base URL (e.g., http://localhost:30000)")
    parser.add_argument("--scene-id", required=True, help="Foundry scene ID to update")
    parser.add_argument("--api-key", help="Foundry API key (if authentication required)")
    parser.add_argument("--websocket-port", type=int, default=30001, help="WebSocket port for Foundry")
    parser.add_argument("--surface-width", type=int, default=1000, help="Surface width in units")
    parser.add_argument("--surface-height", type=int, default=1000, help="Surface height in units")
    parser.add_argument("--no-display", action="store_true", help="Run without display window")
    
    args = parser.parse_args()
    
    # Create Foundry configuration
    foundry_config = FoundryConfig(
        base_url=args.foundry_url,
        scene_id=args.scene_id,
        api_key=args.api_key,
        websocket_port=args.websocket_port
    )
    
    # Create tracker
    tracker = FoundryQRTracker(foundry_config, args.surface_width, args.surface_height)
    
    # Initialize camera
    if not tracker.initialize_camera():
        return
    
    # Calibrate surface
    if not tracker.calibrate():
        logger.error("Calibration failed!")
        return
    
    # Run tracking
    asyncio.run(tracker.run_async(display=not args.no_display))


if __name__ == "__main__":
    main()
