#!/usr/bin/env python3
"""
Foundry VTT ArUco Token Tracker
==============================

A Python script that uses the Raspberry Pi camera to track ArUco markers
and sends real-time position updates to Foundry Virtual Tabletop.

ArUco Marker Schema (Optimized for smaller markers):
- Corner markers: IDs 0-3 (TL=0, TR=1, BR=2, BL=3)
- Player markers: IDs 10-25 (16 players maximum)
- Item markers: IDs 30-61 (32 standard gaming items)
- Custom markers: IDs 62+ (user-defined tokens)

Requirements:
- Raspberry Pi with camera module
- Python packages: picamera2, opencv-python, numpy, websockets, requests
- Foundry VTT with compatible module

Installation:
sudo apt update
sudo apt install python3-opencv python3-numpy
pip3 install picamera2 websockets requests aiohttp opencv-python numpy

Usage:
python3 foundry_aruco_tracker.py --foundry-url "http://192.168.1.50:30000" --scene-id "your-scene-id"
"""

import cv2
import numpy as np
from picamera2 import Picamera2
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
class ArucoToken:
    """Represents a detected ArUco marker token."""
    id: int
    x: float
    y: float
    confidence: float
    last_seen: float
    corners: List[Tuple[int, int]]
    marker_type: str
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
        self.token_mapping = {}  # ArUco ID -> Foundry Token ID
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
                "source": "aruco_tracker",
                "scene_id": self.config.scene_id,
                "tracker_host": "raspberry_pi",
                "marker_system": "aruco",
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
    
    async def update_token_position_ws(self, aruco_token: ArucoToken, surface_width: float, surface_height: float):
        """Update token position via WebSocket."""
        if not self.connection_active or not self.websocket:
            return False
        
        try:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                aruco_token.x, aruco_token.y, surface_width, surface_height)
            
            update_message = {
                "type": "token_update",
                "scene_id": self.config.scene_id,
                "aruco_id": aruco_token.id,
                "token_id": aruco_token.foundry_token_id,
                "x": foundry_x,
                "y": foundry_y,
                "confidence": aruco_token.confidence,
                "marker_type": aruco_token.marker_type
            }
            
            await self.websocket.send(json.dumps(update_message))
            return True
            
        except Exception as e:
            logger.error(f"Failed to send WebSocket update: {e}")
            return False
    
    def update_token_position_http(self, aruco_token: ArucoToken, surface_width: float, surface_height: float):
        """Update token position via HTTP API."""
        try:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                aruco_token.x, aruco_token.y, surface_width, surface_height)
            
            # Foundry API endpoint for updating tokens
            url = f"{self.config.base_url}/api/tokens/{aruco_token.foundry_token_id}"
            
            payload = {
                "x": foundry_x,
                "y": foundry_y,
                "_id": aruco_token.foundry_token_id
            }
            
            response = self.session.patch(url, json=payload)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to send HTTP update: {e}")
            return False
    
    def create_or_find_token(self, aruco_id: int, marker_type: str) -> Optional[str]:
        """Create or find a token in Foundry for the ArUco ID."""
        try:
            # Generate token name based on marker type and ID
            if marker_type == 'player':
                player_num = aruco_id - 10 + 1  # IDs 10-25 become Players 1-16
                token_name = f"Player_{player_num:02d}"
            elif marker_type == 'item':
                # Standard item names
                item_names = {
                    30: "Goblin", 31: "Orc", 32: "Skeleton", 33: "Dragon", 34: "Troll", 35: "Wizard_Enemy", 36: "Beast", 37: "Demon",
                    40: "Treasure_Chest", 41: "Magic_Item", 42: "Gold_Pile", 43: "Potion", 44: "Weapon", 45: "Armor", 46: "Scroll", 47: "Key",
                    50: "NPC_Merchant", 51: "NPC_Guard", 52: "NPC_Noble", 53: "NPC_Innkeeper", 54: "NPC_Priest",
                    55: "Door", 56: "Trap", 57: "Fire_Hazard", 58: "Altar", 59: "Portal", 60: "Vehicle", 61: "Objective"
                }
                token_name = item_names.get(aruco_id, f"Item_{aruco_id}")
            else:
                token_name = f"Custom_{aruco_id}"
            
            # First, try to find existing token
            url = f"{self.config.base_url}/api/scenes/{self.config.scene_id}/tokens"
            response = self.session.get(url)
            
            if response.status_code == 200:
                tokens = response.json()
                for token in tokens:
                    if (token.get('name') == token_name or 
                        token.get('flags', {}).get('aruco_id') == aruco_id):
                        logger.info(f"Found existing token for ArUco {aruco_id}: {token['_id']}")
                        return token['_id']
            
            # Create new token if not found
            create_payload = {
                "name": token_name,
                "x": 100,
                "y": 100,
                "img": "icons/svg/mystery-man.svg",  # Default token image
                "width": 1,
                "height": 1,
                "flags": {
                    "aruco_id": aruco_id,
                    "aruco_tracker": True,
                    "marker_type": marker_type
                }
            }
            
            response = self.session.post(url, json=create_payload)
            if response.status_code == 201:
                token_data = response.json()
                logger.info(f"Created new token for ArUco {aruco_id}: {token_data['_id']}")
                return token_data['_id']
            
        except Exception as e:
            logger.error(f"Failed to create/find token for ArUco {aruco_id}: {e}")
        
        return None
    
    def export_to_foundry_module(self, tokens: List[ArucoToken], surface_width: float, surface_height: float):
        """Export token data to a file that a Foundry module can read."""
        output_data = {
            "timestamp": time.time(),
            "scene_id": self.config.scene_id,
            "marker_system": "aruco",
            "tokens": []
        }
        
        for token in tokens:
            foundry_x, foundry_y = self.surface_to_foundry_coords(
                token.x, token.y, surface_width, surface_height)
            
            token_data = {
                "aruco_id": token.id,
                "foundry_token_id": token.foundry_token_id,
                "x": foundry_x,
                "y": foundry_y,
                "confidence": token.confidence,
                "marker_type": token.marker_type,
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
        
        # ArUco corner mapping - optimized schema
        self.corner_mapping = {
            0: 'CORNER_TL',  # Top-Left
            1: 'CORNER_TR',  # Top-Right
            2: 'CORNER_BR',  # Bottom-Right
            3: 'CORNER_BL'   # Bottom-Left
        }
        
        # ID ranges for optimized schema (smaller markers)
        self.player_id_range = (10, 25)  # 16 players
        self.item_id_range = (30, 61)    # 32 standard items
    
    def calibrate_surface(self, frame: np.ndarray, tracker) -> bool:
        """Calibrate the surface by detecting corner markers or manual selection."""
        print("Surface calibration mode:")
        print("1. Place corner markers (ArUco IDs: 0=TL, 1=TR, 2=BR, 3=BL)")
        print("2. Or press 'c' to manually select corners")
        
        if self._detect_corner_markers(frame, tracker):
            return True
        
        return self._manual_corner_selection(frame)
    
    def _detect_corner_markers(self, frame: np.ndarray, tracker) -> bool:
        """Detect corner markers automatically."""
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Use the tracker's detection method to maintain consistency
        if hasattr(tracker, 'use_new_api') and tracker.use_new_api and tracker.detector is not None:
            # New API (OpenCV 4.7+)
            corners, ids, rejected = tracker.detector.detectMarkers(gray)
        else:
            # Legacy API (OpenCV < 4.7)
            corners, ids, rejected = cv2.aruco.detectMarkers(
                gray, tracker.dictionary, parameters=tracker.parameters)
        
        corner_positions = {}
        
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                if marker_id in self.corner_mapping:
                    # Get center point of ArUco marker
                    marker_corners = corners[i][0]  # Shape: (4, 2)
                    center_x = int(np.mean(marker_corners[:, 0]))
                    center_y = int(np.mean(marker_corners[:, 1]))
                    corner_name = self.corner_mapping[marker_id]
                    corner_positions[corner_name] = (center_x, center_y)
        
        if len(corner_positions) == 4:
            self.surface_corners = np.array([
                corner_positions['CORNER_TL'],
                corner_positions['CORNER_TR'],
                corner_positions['CORNER_BR'],
                corner_positions['CORNER_BL']
            ], dtype=np.float32)
            self._calculate_transform_matrix()
            print("Surface calibrated using ArUco corner markers!")
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


class FoundryArucoTracker:
    """Main ArUco tracking system with Foundry VTT integration."""
    
    def __init__(self, foundry_config: FoundryConfig, surface_width: int = 1000, surface_height: int = 1000):
        self.picam = None
        self.calibrator = SurfaceCalibrator()
        self.calibrator.surface_width = surface_width
        self.calibrator.surface_height = surface_height
        
        # Initialize ArUco detector with backward compatibility
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.parameters = cv2.aruco.DetectorParameters_create()
        
        # Check OpenCV version for detector initialization
        self.opencv_version = cv2.__version__
        opencv_major = int(self.opencv_version.split('.')[0])
        opencv_minor = int(self.opencv_version.split('.')[1])
        
        # Use new ArucoDetector class if available (OpenCV 4.7+)
        if opencv_major > 4 or (opencv_major == 4 and opencv_minor >= 7):
            try:
                self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
                self.use_new_api = True
            except AttributeError:
                self.detector = None
                self.use_new_api = False
        else:
            self.detector = None
            self.use_new_api = False
        
        self.foundry = FoundryIntegrator(foundry_config)
        self.tracked_tokens: Dict[int, ArucoToken] = {}
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
            logger.info(f"OpenCV version: {self.opencv_version}")
            logger.info(f"ArUco API: {'New (4.7+)' if self.use_new_api else 'Legacy (<4.7)'}")
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
        return self.calibrator.calibrate_surface(frame, self)
    
    def detect_aruco_markers(self, frame: np.ndarray) -> List[ArucoToken]:
        """Detect ArUco markers in the current frame."""
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Detect markers using appropriate API
        if self.use_new_api and self.detector is not None:
            # New API (OpenCV 4.7+)
            corners, ids, rejected = self.detector.detectMarkers(gray)
        else:
            # Legacy API (OpenCV < 4.7)
            corners, ids, rejected = cv2.aruco.detectMarkers(
                gray, self.dictionary, parameters=self.parameters)
        
        detected_tokens = []
        current_time = time.time()
        
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                try:
                    # Skip corner markers for token tracking
                    if marker_id in [0, 1, 2, 3]:
                        continue
                    
                    # Get marker corners
                    marker_corners = corners[i][0]  # Shape: (4, 2)
                    corner_points = [(int(x), int(y)) for x, y in marker_corners]
                    
                    # Calculate center point
                    center_x = int(np.mean(marker_corners[:, 0]))
                    center_y = int(np.mean(marker_corners[:, 1]))
                    
                    # Convert to surface coordinates
                    surface_x, surface_y = self.calibrator.camera_to_surface_coords(
                        center_x, center_y)
                    
                    # Calculate confidence based on marker area and shape quality
                    marker_area = cv2.contourArea(marker_corners)
                    confidence = min(1.0, marker_area / 10000.0)
                    
                    # Additional confidence check: how square is the marker?
                    rect = cv2.minAreaRect(marker_corners)
                    width, height = rect[1]
                    if width > 0 and height > 0:
                        aspect_ratio = min(width, height) / max(width, height)
                        confidence *= aspect_ratio
                    
                    # Determine marker type using optimized schema
                    if self.calibrator.player_id_range[0] <= marker_id <= self.calibrator.player_id_range[1]:
                        marker_type = 'player'
                    elif self.calibrator.item_id_range[0] <= marker_id <= self.calibrator.item_id_range[1]:
                        marker_type = 'item'
                    else:
                        marker_type = 'custom'
                    
                    # Get or create Foundry token ID
                    foundry_token_id = None
                    if marker_id in self.tracked_tokens:
                        foundry_token_id = self.tracked_tokens[marker_id].foundry_token_id
                    else:
                        foundry_token_id = self.foundry.create_or_find_token(marker_id, marker_type)
                    
                    token = ArucoToken(
                        id=marker_id,
                        x=surface_x,
                        y=surface_y,
                        confidence=confidence,
                        last_seen=current_time,
                        corners=corner_points,
                        marker_type=marker_type,
                        foundry_token_id=foundry_token_id
                    )
                    detected_tokens.append(token)
                    
                except Exception as e:
                    logger.error(f"Error processing ArUco marker {marker_id}: {e}")
                    continue
        
        return detected_tokens
    
    def update_tracked_tokens(self, detected_tokens: List[ArucoToken]):
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
                
                # Generate label based on marker type
                if token.marker_type == 'player':
                    player_num = token.id - 10 + 1
                    label = f"P{player_num} | {status_text}"
                elif token.marker_type == 'item':
                    # Short item names for display
                    item_short_names = {
                        30: "Gob", 31: "Orc", 32: "Ske", 33: "Drg", 34: "Trl", 35: "Wiz", 36: "Bst", 37: "Dem",
                        40: "Chr", 41: "Mag", 42: "Gld", 43: "Pot", 44: "Wpn", 45: "Arm", 46: "Scr", 47: "Key",
                        50: "Mer", 51: "Grd", 52: "Nob", 53: "Inn", 54: "Pri", 55: "Dor", 56: "Trp", 57: "Fir",
                        58: "Alt", 59: "Por", 60: "Veh", 61: "Obj"
                    }
                    short_name = item_short_names.get(token.id, f"I{token.id}")
                    label = f"{short_name} | {status_text}"
                else:
                    label = f"C{token.id} | {status_text}"
                
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
        
        # ArUco status
        cv2.putText(overlay_frame, "ArUco Tracking (DICT_6X6_250)", (10, 60),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return overlay_frame
    
    async def run_async(self, display: bool = True):
        """Main async tracking loop."""
        if not self.picam:
            logger.error("Camera not initialized!")
            return
        
        # Connect to Foundry
        await self.foundry.connect_websocket()
        
        self.running = True
        logger.info("Starting Foundry ArUco tracking... Press 'q' to quit, 'r' to recalibrate")
        
        try:
            while self.running:
                frame = self.picam.capture_array()
                detected_tokens = self.detect_aruco_markers(frame)
                self.update_tracked_tokens(detected_tokens)
                
                # Send updates to Foundry
                await self.send_foundry_updates()
                
                if display:
                    overlay_frame = self.draw_overlay(frame)
                    cv2.imshow("Foundry ArUco Tracker", overlay_frame)
                    
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
    parser = argparse.ArgumentParser(description="Foundry VTT ArUco Token Tracker")
    parser.add_argument("--foundry-url", required=True, help="Foundry VTT base URL (e.g., http://192.168.1.50:30000)")
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
    tracker = FoundryArucoTracker(foundry_config, args.surface_width, args.surface_height)
    
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
