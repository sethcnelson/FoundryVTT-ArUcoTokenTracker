#!/usr/bin/env python3
"""
Raspberry Pi QR Code Surface Tracker
====================================

A Python script that uses the Raspberry Pi camera to monitor a flat surface
and track QR codes, providing their identifiers and 2D coordinates.

Requirements:
- Raspberry Pi with camera module
- Python packages: picamera2, opencv-python, pyzbar, numpy

Installation:
sudo apt update
sudo apt install python3-opencv python3-numpy
pip3 install picamera2 pyzbar

Usage:
python3 qr_tracker.py
"""

import cv2
import numpy as np
from picamera2 import Picamera2
from pyzbar import pyzbar
import time
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional
import threading
import queue


@dataclass
class QRToken:
    """Represents a detected QR code token."""
    id: str
    x: float
    y: float
    confidence: float
    last_seen: float
    corners: List[Tuple[int, int]]


class SurfaceCalibrator:
    """Handles calibration of the surface area for coordinate mapping."""
    
    def __init__(self):
        self.surface_corners = None
        self.transform_matrix = None
        self.surface_width = 1000  # Default surface width in units
        self.surface_height = 1000  # Default surface height in units
    
    def calibrate_surface(self, frame: np.ndarray) -> bool:
        """
        Calibrate the surface by detecting corner markers or manual selection.
        Returns True if calibration successful.
        """
        print("Surface calibration mode:")
        print("1. Place 4 corner markers (QR codes with 'CORNER_TL', 'CORNER_TR', 'CORNER_BL', 'CORNER_BR')")
        print("2. Or press 'c' to manually select corners")
        
        # Try automatic corner detection first
        if self._detect_corner_markers(frame):
            return True
        
        # Fall back to manual corner selection
        return self._manual_corner_selection(frame)
    
    def _detect_corner_markers(self, frame: np.ndarray) -> bool:
        """Detect corner markers automatically."""
        qr_codes = pyzbar.decode(frame)
        corners = {}
        
        for qr in qr_codes:
            data = qr.data.decode('utf-8')
            if data in ['CORNER_TL', 'CORNER_TR', 'CORNER_BL', 'CORNER_BR']:
                # Get center point of QR code
                points = qr.polygon
                if len(points) == 4:
                    center_x = sum(p.x for p in points) // len(points)
                    center_y = sum(p.y for p in points) // len(points)
                    corners[data] = (center_x, center_y)
        
        if len(corners) == 4:
            self.surface_corners = np.array([
                corners['CORNER_TL'],
                corners['CORNER_TR'],
                corners['CORNER_BR'],
                corners['CORNER_BL']
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
            
            # Draw already selected corners
            for i, corner in enumerate(corners):
                cv2.circle(display_frame, corner, 5, (0, 255, 0), -1)
                cv2.putText(display_frame, corner_names[i], 
                           (corner[0] + 10, corner[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
            
            # Show instruction for next corner
            if len(corners) < 4:
                cv2.putText(display_frame, f"Click {corner_names[len(corners)]} corner",
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            cv2.imshow("Calibration - Click 4 corners", display_frame)
            
            if cv2.waitKey(1) & 0xFF == 27:  # ESC key
                cv2.destroyAllWindows()
                return False
        
        self.surface_corners = np.array(corners, dtype=np.float32)
        self._calculate_transform_matrix()
        cv2.destroyAllWindows()
        print("Surface calibrated manually!")
        return True
    
    def _calculate_transform_matrix(self):
        """Calculate perspective transform matrix."""
        # Define destination points (normalized coordinates)
        dst_points = np.array([
            [0, 0],
            [self.surface_width, 0],
            [self.surface_width, self.surface_height],
            [0, self.surface_height]
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


class QRTracker:
    """Main QR code tracking system."""
    
    def __init__(self, surface_width: int = 1000, surface_height: int = 1000):
        self.picam = None
        self.calibrator = SurfaceCalibrator()
        self.calibrator.surface_width = surface_width
        self.calibrator.surface_height = surface_height
        
        self.tracked_tokens: Dict[str, QRToken] = {}
        self.token_timeout = 2.0  # Remove tokens not seen for 2 seconds
        self.running = False
        
        # Threading for non-blocking output
        self.output_queue = queue.Queue()
        self.callback_functions = []
    
    def initialize_camera(self) -> bool:
        """Initialize the Raspberry Pi camera."""
        try:
            self.picam = Picamera2()
            
            # Configure camera
            config = self.picam.create_preview_configuration(
                main={"size": (1280, 720), "format": "RGB888"}
            )
            self.picam.configure(config)
            self.picam.start()
            
            # Allow camera to warm up
            time.sleep(2)
            print("Camera initialized successfully!")
            return True
            
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            return False
    
    def calibrate(self) -> bool:
        """Calibrate the surface area."""
        if not self.picam:
            print("Camera not initialized!")
            return False
        
        print("Starting surface calibration...")
        frame = self.picam.capture_array()
        return self.calibrator.calibrate_surface(frame)
    
    def add_callback(self, callback_func):
        """Add a callback function to be called when tokens are updated."""
        self.callback_functions.append(callback_func)
    
    def detect_qr_codes(self, frame: np.ndarray) -> List[QRToken]:
        """Detect QR codes in the current frame."""
        qr_codes = pyzbar.decode(frame)
        detected_tokens = []
        current_time = time.time()
        
        for qr in qr_codes:
            try:
                # Decode QR data
                qr_data = qr.data.decode('utf-8')
                
                # Skip corner markers
                if qr_data.startswith('CORNER_'):
                    continue
                
                # Get QR code position (center point)
                points = qr.polygon
                if len(points) >= 4:
                    center_x = sum(p.x for p in points) // len(points)
                    center_y = sum(p.y for p in points) // len(points)
                    
                    # Convert to surface coordinates
                    surface_x, surface_y = self.calibrator.camera_to_surface_coords(
                        center_x, center_y)
                    
                    # Calculate confidence based on QR code size and clarity
                    qr_area = cv2.contourArea(np.array([(p.x, p.y) for p in points]))
                    confidence = min(1.0, qr_area / 10000.0)  # Normalize by expected size
                    
                    # Create token
                    token = QRToken(
                        id=qr_data,
                        x=surface_x,
                        y=surface_y,
                        confidence=confidence,
                        last_seen=current_time,
                        corners=[(p.x, p.y) for p in points]
                    )
                    detected_tokens.append(token)
                    
            except Exception as e:
                print(f"Error processing QR code: {e}")
                continue
        
        return detected_tokens
    
    def update_tracked_tokens(self, detected_tokens: List[QRToken]):
        """Update the tracked tokens list."""
        current_time = time.time()
        
        # Update existing tokens or add new ones
        for token in detected_tokens:
            self.tracked_tokens[token.id] = token
        
        # Remove tokens that haven't been seen recently
        tokens_to_remove = []
        for token_id, token in self.tracked_tokens.items():
            if current_time - token.last_seen > self.token_timeout:
                tokens_to_remove.append(token_id)
        
        for token_id in tokens_to_remove:
            del self.tracked_tokens[token_id]
    
    def get_current_tokens(self) -> List[Dict]:
        """Get current tokens as a list of dictionaries."""
        return [asdict(token) for token in self.tracked_tokens.values()]
    
    def draw_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw tracking overlay on the frame."""
        overlay_frame = frame.copy()
        
        # Draw surface corners if calibrated
        if self.calibrator.surface_corners is not None:
            corners = self.calibrator.surface_corners.astype(int)
            cv2.polylines(overlay_frame, [corners], True, (0, 255, 0), 2)
        
        # Draw tracked tokens
        for token in self.tracked_tokens.values():
            # Draw QR code outline
            if token.corners:
                corners_array = np.array(token.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, (255, 0, 0), 2)
            
            # Draw center point
            camera_coords = None
            if self.calibrator.transform_matrix is not None:
                # Convert surface coords back to camera coords for display
                surface_point = np.array([[[token.x, token.y]]], dtype=np.float32)
                try:
                    camera_point = cv2.perspectiveTransform(
                        surface_point, np.linalg.inv(self.calibrator.transform_matrix))
                    camera_coords = (int(camera_point[0][0][0]), int(camera_point[0][0][1]))
                except:
                    pass
            
            if camera_coords:
                cv2.circle(overlay_frame, camera_coords, 5, (0, 0, 255), -1)
                
                # Draw label
                label = f"{token.id} ({token.x:.1f}, {token.y:.1f})"
                cv2.putText(overlay_frame, label,
                           (camera_coords[0] + 10, camera_coords[1] - 10),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        return overlay_frame
    
    def run(self, display: bool = True, output_file: str = None):
        """Main tracking loop."""
        if not self.picam:
            print("Camera not initialized!")
            return
        
        self.running = True
        print("Starting QR tracking... Press 'q' to quit, 'r' to recalibrate")
        
        try:
            while self.running:
                # Capture frame
                frame = self.picam.capture_array()
                
                # Detect QR codes
                detected_tokens = self.detect_qr_codes(frame)
                
                # Update tracking
                self.update_tracked_tokens(detected_tokens)
                
                # Call callbacks
                current_tokens = self.get_current_tokens()
                for callback in self.callback_functions:
                    try:
                        callback(current_tokens)
                    except Exception as e:
                        print(f"Callback error: {e}")
                
                # Output to file if specified
                if output_file and current_tokens:
                    with open(output_file, 'w') as f:
                        json.dump({
                            'timestamp': time.time(),
                            'tokens': current_tokens
                        }, f, indent=2)
                
                # Display if requested
                if display:
                    overlay_frame = self.draw_overlay(frame)
                    cv2.imshow("QR Tracker", overlay_frame)
                    
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q'):
                        break
                    elif key == ord('r'):
                        print("Recalibrating...")
                        self.calibrate()
                
                # Small delay to prevent overwhelming the system
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping tracker...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the tracking system."""
        self.running = False
        if self.picam:
            self.picam.stop()
        cv2.destroyAllWindows()
        print("Tracker stopped.")


# Example callback function
def print_tokens(tokens):
    """Example callback that prints current tokens."""
    if tokens:
        print(f"\n--- Detected Tokens ({len(tokens)}) ---")
        for token in tokens:
            print(f"ID: {token['id']:15} Position: ({token['x']:6.1f}, {token['y']:6.1f}) "
                  f"Confidence: {token['confidence']:.2f}")
    else:
        print("No tokens detected")


def main():
    """Main function to run the QR tracker."""
    # Create tracker instance
    tracker = QRTracker(surface_width=1000, surface_height=1000)
    
    # Initialize camera
    if not tracker.initialize_camera():
        return
    
    # Calibrate surface
    if not tracker.calibrate():
        print("Calibration failed!")
        return
    
    # Add callback for printing tokens
    tracker.add_callback(print_tokens)
    
    # Start tracking
    tracker.run(display=True, output_file="qr_tracking_output.json")


if __name__ == "__main__":
    main()
