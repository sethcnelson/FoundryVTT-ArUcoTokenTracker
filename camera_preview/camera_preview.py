#!/usr/bin/env python3
"""
Raspberry Pi Camera Preview with ArUco Marker Overlays
====================================================

A lightweight camera preview tool that shows:
- Live camera feed at 1 FPS
- Bounding box overlay for corner ArUco markers
- Shape overlays for player tokens
- Surface calibration status

ArUco Marker Schema:
- Corner markers: IDs 0-3 (TL=0, TR=1, BR=2, BL=3)
- Player markers: IDs 10-99 (90 unique players)

Usage:
python3 aruco_preview.py [options]

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
import time
import argparse
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
import os
from datetime import datetime


@dataclass
class DetectedMarker:
    """Represents a detected ArUco marker with metadata."""
    id: int
    center: Tuple[int, int]
    corners: List[Tuple[int, int]]
    is_corner: bool
    confidence: float
    marker_type: str


class ArucoPreviewApp:
    """Camera preview application with ArUco marker overlays."""
    
    def __init__(self, fps: float = 1.0, resolution: Tuple[int, int] = (1280, 720)):
        self.picam = None
        self.fps = fps
        self.resolution = resolution
        self.running = False
        
        # Initialize ArUco detector
        self.dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        self.parameters = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.dictionary, self.parameters)
        
        # Detection toggles
        self.detect_corners = True
        self.detect_players = True
        self.show_help = True
        self.fullscreen = False
        
        # Visual settings
        self.colors = {
            'corner_box': (0, 255, 0),      # Green for corner bounding box
            'corner_marker': (0, 255, 255), # Yellow for corner markers
            'player_circle': (255, 0, 0),   # Red for player tokens
            'player_text': (255, 255, 255), # White for player text
            'surface_box': (0, 255, 0),     # Green for surface boundary
            'info_text': (255, 255, 255),   # White for info text
            'help_bg': (0, 0, 0),           # Black background for help
        }
        
        # ArUco marker mappings - optimized for smaller markers
        self.corner_mapping = {
            0: 'CORNER_TL',  # Top-Left
            1: 'CORNER_TR',  # Top-Right
            2: 'CORNER_BR',  # Bottom-Right
            3: 'CORNER_BL'   # Bottom-Left
        }
        
        # ID ranges for optimized schema
        self.player_id_range = (10, 25)  # 16 players
        self.item_id_range = (30, 61)    # 32 standard items
        
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
            print("ArUco detector ready (DICT_6X6_250)")
            return True
            
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            return False
    
    def detect_aruco_markers(self, frame: np.ndarray) -> List[DetectedMarker]:
        """Detect and classify ArUco markers in the frame."""
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        
        # Detect markers
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        detected_markers = []
        if ids is not None:
            for i, marker_id in enumerate(ids.flatten()):
                # Get marker corners
                marker_corners = corners[i][0]  # Shape: (4, 2)
                corner_points = [(int(x), int(y)) for x, y in marker_corners]
                
                # Calculate center point
                center_x = int(np.mean(marker_corners[:, 0]))
                center_y = int(np.mean(marker_corners[:, 1]))
                center = (center_x, center_y)
                
                # Calculate confidence based on marker area and shape quality
                marker_area = cv2.contourArea(marker_corners)
                # Simple confidence metric based on area (larger = more confident)
                confidence = min(1.0, marker_area / 10000.0)
                
                # Additional confidence check: how square is the marker?
                rect = cv2.minAreaRect(marker_corners)
                width, height = rect[1]
                if width > 0 and height > 0:
                    aspect_ratio = min(width, height) / max(width, height)
                    confidence *= aspect_ratio  # Penalize non-square markers
                
                # Determine marker type
                is_corner = marker_id in self.corner_mapping
                if is_corner:
                    marker_type = 'corner'
                elif self.player_id_range[0] <= marker_id <= self.player_id_range[1]:
                    marker_type = 'player'
                elif self.item_id_range[0] <= marker_id <= self.item_id_range[1]:
                    marker_type = 'item'
                else:
                    marker_type = 'custom'
                
                detected_marker = DetectedMarker(
                    id=marker_id,
                    center=center,
                    corners=corner_points,
                    is_corner=is_corner,
                    confidence=confidence,
                    marker_type=marker_type
                )
                detected_markers.append(detected_marker)
        
        return detected_markers
    
    def update_surface_calibration(self, detected_markers: List[DetectedMarker]):
        """Update surface calibration based on corner markers."""
        # Update corner marker positions
        for marker in detected_markers:
            if marker.is_corner and marker.id in self.corner_mapping:
                corner_name = self.corner_mapping[marker.id]
                self.corner_markers[corner_name] = marker.center
        
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
    
    def draw_corner_overlays(self, frame: np.ndarray, detected_markers: List[DetectedMarker]) -> np.ndarray:
        """Draw overlays for corner ArUco markers."""
        overlay_frame = frame.copy()
        
        for marker in detected_markers:
            if marker.is_corner and self.detect_corners:
                # Draw marker outline
                corners_array = np.array(marker.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, self.colors['corner_marker'], 2)
                
                # Draw center point
                cv2.circle(overlay_frame, marker.center, 8, self.colors['corner_marker'], -1)
                
                # Draw corner label
                corner_name = self.corner_mapping.get(marker.id, f"ID_{marker.id}")
                label = corner_name.replace('CORNER_', '')
                cv2.putText(overlay_frame, label, 
                           (marker.center[0] + 15, marker.center[1] - 15),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['corner_marker'], 2)
                
                # Draw marker ID
                cv2.putText(overlay_frame, str(marker.id), 
                           (marker.center[0] - 10, marker.center[1] + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['corner_marker'], 2)
        
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
    
    def draw_player_overlays(self, frame: np.ndarray, detected_markers: List[DetectedMarker]) -> np.ndarray:
        """Draw overlays for player token ArUco markers."""
        overlay_frame = frame.copy()
        
        for marker in detected_markers:
            if (marker.marker_type == 'player' or marker.marker_type == 'item') and self.detect_players:
                # Different colors for different marker types
                if marker.marker_type == 'player':
                    color = self.colors['player_circle']  # Red for players
                    shape_style = 'circle'
                else:  # item markers
                    color = (255, 165, 0)  # Orange for items
                    shape_style = 'square'
                
                # Draw different shapes based on confidence and type
                if marker.confidence > 0.8:
                    # High confidence
                    if shape_style == 'circle':
                        cv2.circle(overlay_frame, marker.center, 20, color, -1)
                        cv2.circle(overlay_frame, marker.center, 22, self.colors['player_text'], 2)
                    else:  # square for items
                        cv2.rectangle(overlay_frame,
                                     (marker.center[0] - 20, marker.center[1] - 20),
                                     (marker.center[0] + 20, marker.center[1] + 20),
                                     color, -1)
                        cv2.rectangle(overlay_frame,
                                     (marker.center[0] - 22, marker.center[1] - 22),
                                     (marker.center[0] + 22, marker.center[1] + 22),
                                     self.colors['player_text'], 2)
                elif marker.confidence > 0.5:
                    # Medium confidence: outline only
                    if shape_style == 'circle':
                        cv2.circle(overlay_frame, marker.center, 20, color, 3)
                    else:  # square outline
                        cv2.rectangle(overlay_frame,
                                     (marker.center[0] - 20, marker.center[1] - 20),
                                     (marker.center[0] + 20, marker.center[1] + 20),
                                     color, 3)
                else:
                    # Low confidence: dashed
                    if shape_style == 'circle':
                        self.draw_dashed_circle(overlay_frame, marker.center, 20, color, 2)
                    else:
                        self.draw_dashed_square(overlay_frame, marker.center, 20, color, 2)
                
                # Draw marker outline
                corners_array = np.array(marker.corners, dtype=int)
                cv2.polylines(overlay_frame, [corners_array], True, color, 1)
                
                # Generate appropriate label
                if marker.marker_type == 'player':
                    player_num = marker.id - self.player_id_range[0] + 1
                    label = f"P{player_num}"
                elif marker.marker_type == 'item':
                    # Use a short item name based on ID
                    item_names = {
                        30: "Gob", 31: "Orc", 32: "Ske", 33: "Drg", 34: "Trl", 35: "Wiz", 36: "Bst", 37: "Dem",
                        40: "Chr", 41: "Mag", 42: "Gld", 43: "Pot", 44: "Wpn", 45: "Arm", 46: "Scr", 47: "Key",
                        50: "Mer", 51: "Grd", 52: "Nob", 53: "Inn", 54: "Pri", 55: "Dor", 56: "Trp", 57: "Fir",
                        58: "Alt", 59: "Por", 60: "Veh", 61: "Obj"
                    }
                    label = item_names.get(marker.id, f"I{marker.id}")
                else:
                    label = f"C{marker.id}"
                
                # Calculate text size for centering
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
                text_x = marker.center[0] - text_size[0] // 2
                text_y = marker.center[1] + text_size[1] // 2
                
                # Draw text with background
                cv2.rectangle(overlay_frame, 
                             (text_x - 2, text_y - text_size[1] - 2),
                             (text_x + text_size[0] + 2, text_y + 2),
                             (0, 0, 0), -1)
                cv2.putText(overlay_frame, label, (text_x, text_y),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['player_text'], 2)
                
                # Show marker ID and confidence
                info_text = f"ID:{marker.id} {marker.confidence:.2f}"
                cv2.putText(overlay_frame, info_text,
                           (marker.center[0] + 25, marker.center[1] + 25),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, self.colors['player_text'], 1)
            
            # Handle custom markers (62+)
            elif marker.marker_type == 'custom' and self.detect_players:
                # Draw custom markers with different style
                cv2.circle(overlay_frame, marker.center, 15, (255, 0, 255), 2)  # Magenta circle
                
                label = f"C{marker.id}"
                cv2.putText(overlay_frame, label,
                           (marker.center[0] + 20, marker.center[1]),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 1)
        
        return overlay_frame
    
    def draw_dashed_circle(self, frame: np.ndarray, center: Tuple[int, int], 
                          radius: int, color: Tuple[int, int, int], thickness: int):
        """Draw a dashed circle."""
        # Draw circle as series of small arcs
        for i in range(0, 360, 20):
            start_angle = i
            end_angle = i + 10
            cv2.ellipse(frame, center, (radius, radius), 0, start_angle, end_angle, color, thickness)
    
    def draw_dashed_square(self, frame: np.ndarray, center: Tuple[int, int], 
                          size: int, color: Tuple[int, int, int], thickness: int):
        """Draw a dashed square."""
        # Draw square as series of small line segments
        half_size = size
        corners = [
            (center[0] - half_size, center[1] - half_size),  # Top-left
            (center[0] + half_size, center[1] - half_size),  # Top-right
            (center[0] + half_size, center[1] + half_size),  # Bottom-right
            (center[0] - half_size, center[1] + half_size)   # Bottom-left
        ]
        
        # Draw dashed lines for each side
        for i in range(4):
            start = corners[i]
            end = corners[(i + 1) % 4]
            
            # Calculate line segments
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            line_length = int((dx**2 + dy**2)**0.5)
            
            if line_length > 0:
                num_segments = max(1, line_length // 8)  # 8 pixel segments
                for j in range(0, num_segments, 2):  # Every other segment
                    seg_start_x = start[0] + int(dx * j / num_segments)
                    seg_start_y = start[1] + int(dy * j / num_segments)
                    seg_end_x = start[0] + int(dx * min(j + 1, num_segments) / num_segments)
                    seg_end_y = start[1] + int(dy * min(j + 1, num_segments) / num_segments)
                    
                    cv2.line(frame, (seg_start_x, seg_start_y), (seg_end_x, seg_end_y), color, thickness)
    
    def draw_info_overlay(self, frame: np.ndarray, detected_markers: List[DetectedMarker]) -> np.ndarray:
        """Draw information overlay with statistics."""
        overlay_frame = frame.copy()
        
        # Count detections by type
        corner_count = sum(1 for m in detected_markers if m.is_corner)
        player_count = sum(1 for m in detected_markers if m.marker_type == 'player')
        item_count = sum(1 for m in detected_markers if m.marker_type == 'item')
        custom_count = sum(1 for m in detected_markers if m.marker_type == 'custom')
        
        # Prepare info text
        info_lines = [
            f"ArUco Detection (6x6_250) - Optimized",
            f"FPS: {self.fps:.1f}",
            f"Resolution: {self.resolution[0]}x{self.resolution[1]}",
            f"Corners: {corner_count}/4",
            f"Players: {player_count}/16",
            f"Items: {item_count}/32",
            f"Custom: {custom_count}",
            f"Surface: {'CALIBRATED' if self.surface_corners else 'NOT CALIBRATED'}",
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        ]
        
        # Draw info panel background
        panel_height = len(info_lines) * 25 + 20
        cv2.rectangle(overlay_frame, (10, 10), (280, panel_height), (0, 0, 0), -1)
        cv2.rectangle(overlay_frame, (10, 10), (280, panel_height), self.colors['info_text'], 1)
        
        # Draw info text
        for i, line in enumerate(info_lines):
            y_pos = 30 + i * 25
            color = self.colors['corner_marker'] if i == 0 else self.colors['info_text']
            cv2.putText(overlay_frame, line, (20, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 1)
        
        return overlay_frame
    
    def draw_help_overlay(self, frame: np.ndarray) -> np.ndarray:
        """Draw help overlay with keyboard controls."""
        if not self.show_help:
            return frame
        
        overlay_frame = frame.copy()
        
        help_lines = [
            "ARUCO CONTROLS:",
            "q/ESC - Quit",
            "c - Toggle corner detection",
            "p - Toggle player/item detection", 
            "s - Save current frame",
            "f - Toggle fullscreen",
            "h - Toggle this help",
            "",
            "OPTIMIZED MARKER SCHEMA:",
            "Corner: IDs 0-3",
            "Player: IDs 10-25 (16 max)",
            "Items: IDs 30-61 (32 types)",
            "Custom: IDs 62+",
            "",
            "VISUAL MARKERS:",
            "Players: Red circles",
            "Items: Orange squares", 
            "Custom: Magenta circles",
            "",
            "STATUS:",
            f"Corners: {'ON' if self.detect_corners else 'OFF'}",
            f"Players/Items: {'ON' if self.detect_players else 'OFF'}",
            f"Fullscreen: {'ON' if self.fullscreen else 'OFF'}"
        ]
        
        # Calculate help panel size
        panel_width = 320
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
            if line.startswith("ARUCO") or line.startswith("MARKER") or line.startswith("STATUS"):
                color = self.colors['corner_marker']
            else:
                color = self.colors['info_text']
            
            cv2.putText(overlay_frame, line, (start_x + 10, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
        
        return overlay_frame
    
    def save_frame(self, frame: np.ndarray):
        """Save the current frame to disk."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"aruco_preview_{timestamp}_{self.save_counter:03d}.jpg"
        
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
                cv2.namedWindow("ArUco Camera Preview", cv2.WND_PROP_FULLSCREEN)
                cv2.setWindowProperty("ArUco Camera Preview", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
            else:
                cv2.namedWindow("ArUco Camera Preview", cv2.WINDOW_NORMAL)
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
        print("Starting ArUco Camera Preview...")
        print("Marker schema: Corners=0-3, Players=10-99, Custom=100+")
        print("Press 'h' to toggle help, 'q' to quit")
        
        # Create window
        cv2.namedWindow("ArUco Camera Preview", cv2.WINDOW_NORMAL)
        
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
                
                # Detect ArUco markers
                detected_markers = self.detect_aruco_markers(frame)
                
                # Update surface calibration
                self.update_surface_calibration(detected_markers)
                
                # Apply overlays
                display_frame = frame.copy()
                display_frame = self.draw_corner_overlays(display_frame, detected_markers)
                display_frame = self.draw_player_overlays(display_frame, detected_markers)
                display_frame = self.draw_info_overlay(display_frame, detected_markers)
                display_frame = self.draw_help_overlay(display_frame)
                
                # Display frame
                cv2.imshow("ArUco Camera Preview", display_frame)
                
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
    parser = argparse.ArgumentParser(description="ArUco Camera Preview Tool")
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
    app = ArucoPreviewApp(fps=args.fps, resolution=resolution)
    
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
