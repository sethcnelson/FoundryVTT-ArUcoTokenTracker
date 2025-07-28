#!/usr/bin/env python3
"""
Raspberry Pi Camera Preview with QR Code Overlays
================================================

A lightweight camera preview tool that shows:
- Live camera feed at 1 FPS
- Bounding box overlay for corner QR codes
- Shape overlays for player tokens
- Surface calibration status

Usage:
python3 camera_preview.py [options]

Controls:
- 'q' or ESC: Quit
- 'c': Toggle corner detection
- 'p': Toggle player token detection  
- 's': Save current frame
- 'f': Toggle fullscreen
- 'h': Show/hide help overlay
"""

import cv2
import numpy as np
from picamera2 import Picamera2
from pyzbar import pyzbar
import time
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import os
from datetime import datetime


@dataclass
class DetectedQR:
    """Represents a detected QR code with metadata."""
    id: str
    center: Tuple[int, int]
    corners: List[Tuple[int, int]]
    is_corner: bool
    confidence: float


class QRPreviewApp:
    """Camera preview application with QR code overlays."""
    
    def __init__(self, fps: float = 1.0, resolution: Tuple[int, int] = (1280, 720)):
        self.picam = None
        self.fps = fps
        self.resolution = resolution
        self.running = False
        
        # Detection toggles
        self.detect_corners = True
        self.detect_players = True
        self.show_help = True
        self.fullscreen = False
        
        # Visual settings
        self.colors = {
            'corner_box': (0, 255, 0),      # Green for corner bounding box
            'corner_marker': (0, 255, 255), # Yellow for corner QR codes
            'player_circle': (255, 0, 0),   # Red for player tokens
            'player_text': (255, 255, 255), # White for player text
            'surface_box': (0, 255, 0),     # Green for surface boundary
            'info_text': (255, 255, 255),   # White for info text
            'help_bg': (0, 0, 0),           # Black background for help
        }
        
        # Surface calibration
        self.corner_markers = {}  # Store detected corner positions
        self.surface_corners = None
        
        # Frame saving
        self.save_counter = 0
    
    def initialize_camera(self) -> bool:
        """Initialize the Raspberry Pi camera."""
        try:
            self.picam = Picamera2()
            
            # Configure camera for preview
            config = self.picam.create_preview_configuration(
                main={"size": self.resolution, "format": "RGB888"}
            )
            self.picam.configure(config)
            self.picam.start()
            
            # Allow camera to warm up
            time.sleep(2)
            print(f"Camera initialized: {self.resolution[0]}x{self.resolution[1]} @ {self.fps} FPS")
            return True
            
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            return False
    
    def detect_qr_codes(self, frame: np.ndarray) -> List[DetectedQR]:
        """Detect and classify QR codes in the frame."""
        qr_codes = pyzbar.decode(frame)
        detected_qrs = []
        
        for qr in qr_codes:
            try:
                # Decode QR data
                qr_data = qr.data.decode('utf-8')
                
                # Get corner points
                points = qr.polygon
                if len(points) >= 4:
                    corners = [(p.x, p.y) for p in points]
                    
                    # Calculate center point
                    center_x = sum(p[0] for p in corners) // len(corners)
                    center_y = sum(p[1] for p in corners) // len(corners)
                    center = (center_x, center_y)
                    
                    # Calculate confidence based on QR code size
                    qr_area = cv2.contourArea(np.array(corners))
                    confidence = min(1.0, qr_area / 10000.0)
                    
                    # Determine if this is a corner marker
                    is_corner = qr_data.startswith('CORNER_')
                    
                    detected_qr = DetectedQR(
                        id=qr_data,
                        center=center,
                        corners=corners,
                        is_corner=is_corner,
                        confidence=confidence
                    )
                    detected_qrs.append(detected_qr)
                    
            except Exception as e:
                print(f"Error processing QR code: {e}")
                continue
        
        return detected_qrs
    
    def update_surface_calibration(self, detected_qrs: List[DetectedQR]):
        """Update surface calibration based on corner markers."""
        # Update corner marker positions
        for qr in detected_qrs:
            if qr.is_corner:
                self.corner_markers[qr.id] = qr.center
        
        # Check if we have all four corners
        required_corners = ['CORNER_TL', 'CORNER_TR', 'CORNER_BL', 'CORNER_BR']
        if all(corner in self.corner_markers for corner in required_corners):
            self.surface_corners = [
                self.corner_markers['CORNER_TL'],
                self.corner_markers['CORNER_TR'],
                self.corner_markers['CORNER_BR'],
                self.corner_markers['CORNER_BL']
            ]
        else:
            self.surface_corners = None
    
    def draw_corner_overlays(self, frame: np.ndarray, detected_qrs: List[DetectedQR]) -> np.ndarray:
        """Draw overlays for corner QR codes."""
        overlay_frame = frame.copy()
        
        for qr in detected_qrs:
            if qr.is_corner and self.detect_corners:
                # Draw QR code outline
                corners_array = np.array(qr.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, self.colors['corner_marker'], 2)
                
                # Draw center point
                cv2.circle(overlay_frame, qr.center, 8, self.colors['corner_marker'], -1)
                
                # Draw corner label
                label = qr.id.replace('CORNER_', '')
                cv2.putText(overlay_frame, label, 
                           (qr.center[0] + 15, qr.center[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['corner_marker'], 2)
        
        # Draw surface bounding box if all corners detected
        if self.surface_corners and self.detect_corners:
            surface_array = np.array(self.surface_corners, dtype=int)
            cv2.polylines(overlay_frame, [surface_array], True, self.colors['surface_box'], 3)
            
            # Add "SURFACE" label
            if self.surface_corners:
                center_x = sum(p[0] for p in self.surface_corners) // 4
                center_y = sum(p[1] for p in self.surface_corners) // 4
                cv2.putText(overlay_frame, "SURFACE", 
                           (center_x - 40, center_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 1.0, self.colors['surface_box'], 2)
        
        return overlay_frame
    
    def draw_player_overlays(self, frame: np.ndarray, detected_qrs: List[DetectedQR]) -> np.ndarray:
        """Draw overlays for player token QR codes."""
        overlay_frame = frame.copy()
        
        for qr in detected_qrs:
            if not qr.is_corner and self.detect_players:
                # Draw different shapes based on confidence or token type
                if qr.confidence > 0.8:
                    # High confidence: filled circle
                    cv2.circle(overlay_frame, qr.center, 20, self.colors['player_circle'], -1)
                    cv2.circle(overlay_frame, qr.center, 22, self.colors['player_text'], 2)
                elif qr.confidence > 0.5:
                    # Medium confidence: circle outline
                    cv2.circle(overlay_frame, qr.center, 20, self.colors['player_circle'], 3)
                else:
                    # Low confidence: dashed circle
                    self.draw_dashed_circle(overlay_frame, qr.center, 20, self.colors['player_circle'], 2)
                
                # Draw QR code outline
                corners_array = np.array(qr.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, self.colors['player_circle'], 1)
                
                # Draw player ID
                label = qr.id
                # Truncate long IDs
                if len(label) > 10:
                    label = label[:8] + ".."
                
                # Calculate text size for centering
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                text_x = qr.center[0] - text_size[0] // 2
                text_y = qr.center[1] + text_size[1] // 2
                
                # Draw text with background
                cv2.rectangle(overlay_frame, 
                             (text_x - 2, text_y - text_size[1] - 2),
                             (text_x + text_size[0] + 2, text_y + 2),
                             (0, 0, 0), -1)
                cv2.putText(overlay_frame, label, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['player_text'], 1)
                
                # Show confidence
                conf_text = f"{qr.confidence:.2f}"
                cv2.putText(overlay_frame, conf_text,
                           (qr.center[0] + 25, qr.center[1] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['player_text'], 1)
        
        return overlay_frame
    
    def draw_dashed_circle(self, frame: np.ndarray, center: Tuple[int, int], 
                          radius: int, color: Tuple[int, int, int], thickness: int):
        """Draw a dashed circle."""
        # Draw circle as series of small arcs
        for i in range(0, 360, 20):
            start_angle = i
            end_angle = i + 10
            cv2.ellipse(frame, center, (radius, radius), 0, start_angle, end_angle, color, thickness)
    
    def draw_info_overlay(self, frame: np.ndarray, detected_qrs: List[DetectedQR]) -> np.ndarray:
        """Draw information overlay with statistics."""
        overlay_frame = frame.copy()
        
        # Count detections
        corner_count = sum(1 for qr in detected_qrs if qr.is_corner)
        player_count = sum(1 for qr in detected_qrs if not qr.is_corner)
        
        # Prepare info text
        info_lines = [
            f"FPS: {self.fps:.1f}",
            f"Resolution: {self.resolution[0]}x{self.resolution[1]}",
            f"Corners: {corner_count}/4",
            f"Players: {player_count}",
            f"Surface: {'CALIBRATED' if self.surface_corners else 'NOT CALIBRATED'}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        # Draw info panel background
        panel_height = len(info_lines) * 25 + 20
        cv2.rectangle(overlay_frame, (10, 10), (250, panel_height), (0, 0, 0), -1)
        cv2.rectangle(overlay_frame, (10, 10), (250, panel_height), self.colors['info_text'], 1)
        
        # Draw info text
        for i, line in enumerate(info_lines):
            y_pos = 30 + i * 25
            cv2.putText(overlay_frame, line, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['info_text'], 1)
        
        return overlay_frame
    
    def draw_help_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw help overlay with keyboard controls."""
        if not self.show_help:
            return frame
        
        overlay_frame = frame.copy()
        
        help_lines = [
            "KEYBOARD CONTROLS:",
            "q/ESC - Quit",
            "c - Toggle corner detection",
            "p - Toggle player detection", 
            "s - Save current frame",
            "f - Toggle fullscreen",
            "h - Toggle this help",
            "",
            "STATUS:",
            f"Corners: {'ON' if self.detect_corners else 'OFF'}",
            f"Players: {'ON' if self.detect_players else 'OFF'}",
            f"Fullscreen: {'ON' if self.fullscreen else 'OFF'}"
        ]
        
        # Calculate help panel size
        panel_width = 300
        panel_height = len(help_lines) * 25 + 20
        start_x = frame.shape[1] - panel_width - 10
        start_y = 10
        
        # Draw help panel background
        cv2.rectangle(overlay_frame, (start_x, start_y), 
                     (start_x + panel_width, start_y + panel_height), 
                     self.colors['help_bg'], -1)
        cv2.rectangle(overlay_frame, (start_x, start_y), 
                     (start_x + panel_width, start_y + panel_height), 
                     self.colors['info_text'], 1)
        
        # Draw help text
        for i, line in enumerate(help_lines):
            y_pos = start_y + 20 + i * 25
            color = self.colors['corner_marker'] if line.startswith("KEYBOARD") or line.startswith("STATUS") else self.colors['info_text']
            cv2.putText(overlay_frame, line, (start_x + 10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return overlay_frame
    
    def save_frame(self, frame: np.ndarray):
        """Save the current frame to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"qr_preview_{timestamp}_{self.save_counter:03d}.jpg"
        
        # Create saves directory if it doesn't exist
        os.makedirs("saved_frames", exist_ok=True)
        filepath = os.path.join("saved_frames", filename)
        
        cv2.imwrite(filepath, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        print(f"Frame saved: {filepath}")
        self.save_counter += 1
    
    def handle_keyboard(self) -> bool:
        """Handle keyboard input. Returns False if should quit."""
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q') or key == 27:  # 'q' or ESC
            return False
        elif key == ord('c'):
            self.detect_corners = not self.detect_corners
            print(f"Corner detection: {'ON' if self.detect_corners else 'OFF'}")
        elif key == ord('p'):
            self.detect_players = not self.detect_players
            print(f"Player detection: {'ON' if self.detect_players else 'OFF'}")
        elif key == ord('s'):
            # Save flag will be handled in main loop
            return 'save'
        elif key == ord('f'):
            self.fullscreen = not self.fullscreen
            if self.fullscreen:
                cv2.namedWindow("QR Camera Preview", cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty("QR Camera Preview", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.namedWindow("QR Camera Preview", cv2.WINDOW_NORMAL)
            print(f"Fullscreen: {'ON' if self.fullscreen else 'OFF'}")
        elif key == ord('h'):
            self.show_help = not self.show_help
            print(f"Help overlay: {'ON' if self.show_help else 'OFF'}")
        
        return True
    
    def run(self):
        """Main application loop."""
        if not self.picam:
            print("Camera not initialized!")
            return
        
        self.running = True
        print("Starting QR Camera Preview...")
        print("Press 'h' to toggle help, 'q' to quit")
        
        # Create window
        cv2.namedWindow("QR Camera Preview", cv2.WINDOW_NORMAL)
        
        # Calculate frame time for target FPS
        frame_time = 1.0 / self.fps
        last_frame_time = time.time()
        
        try:
            while self.running:
                current_time = time.time()
                
                # Control frame rate
                if current_time - last_frame_time < frame_time:
                    time.sleep(0.01)  # Small sleep to prevent busy waiting
                    continue
                
                # Capture frame
                frame = self.picam.capture_array()
                
                # Detect QR codes
                detected_qrs = self.detect_qr_codes(frame)
                
                # Update surface calibration
                self.update_surface_calibration(detected_qrs)
                
                # Apply overlays
                display_frame = frame.copy()
                display_frame = self.draw_corner_overlays(display_frame, detected_qrs)
                display_frame = self.draw_player_overlays(display_frame, detected_qrs)
                display_frame = self.draw_info_overlay(display_frame, detected_qrs)
                display_frame = self.draw_help_overlay(display_frame)
                
                # Display frame
                cv2.imshow("QR Camera Preview", display_frame)
                
                # Handle keyboard input
                key_result = self.handle_keyboard()
                if key_result == False:
                    break
                elif key_result == 'save':
                    self.save_frame(display_frame)
                
                last_frame_time = current_time
                
        except KeyboardInterrupt:
            print("\nStopping preview...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the preview application."""
        self.running = False
        if self.picam:
            self.picam.stop()
        cv2.destroyAllWindows()
        print("Preview stopped.")


def main():
    """Main function with command line arguments."""
    parser = argparse.ArgumentParser(description="QR Camera Preview Tool")
    parser.add_argument("--fps", type=float, default=1.0, help="Frame rate (default: 1.0)")
    parser.add_argument("--resolution", default="1280x720", help="Camera resolution (default: 1280x720)")
    parser.add_argument("--no-corners", action="store_true", help="Start with corner detection disabled")
    parser.add_argument("--no-players", action="store_true", help="Start with player detection disabled")
    parser.add_argument("--no-help", action="store_true", help="Start with help overlay hidden")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    
    args = parser.parse_args()
    
    # Parse resolution
    try:
        width, height = map(int, args.resolution.split('x'))
        resolution = (width, height)
    except ValueError:
        print("Invalid resolution format. Use WIDTHxHEIGHT (e.g., 1280x720)")
        return
    
    # Create preview app
    app = QRPreviewApp(fps=args.fps, resolution=resolution)
    
    # Apply startup options
    if args.no_corners:
        app.detect_corners = False
    if args.no_players:
        app.detect_players = False
    if args.no_help:
        app.show_help = False
    if args.fullscreen:
        app.fullscreen = True
    
    # Initialize camera
    if not app.initialize_camera():
        return
    
    # Run preview
    app.run()


if __name__ == "__main__":
    main()
