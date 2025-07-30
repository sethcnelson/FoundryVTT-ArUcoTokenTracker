#!/usr/bin/env python3
"""
ArUco Marker Generator for QR Token Tracker
==========================================

Generates ArUco markers for corner calibration and player tokens.
ArUco markers are faster and more robust than QR codes for tracking.

Usage:
python3 aruco_generator.py [options]

Marker ID Schema:
- Corner markers: IDs 0-3 (TL, TR, BR, BL)
- Player markers: IDs 10-99 (90 unique players)
- Special markers: IDs 100+ (reserved for future use)
"""

import cv2
import numpy as np
import argparse
import os
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
from typing import List, Dict, Tuple


class ArucoMarkerGenerator:
    """Generate ArUco markers with labels and documentation."""
    
    def __init__(self, dictionary=cv2.aruco.DICT_6X6_250, marker_size=200, border_bits=1):
        """
        Initialize the ArUco marker generator.
        
        Args:
            dictionary: ArUco dictionary to use
            marker_size: Size of marker in pixels
            border_bits: White border size around marker
        """
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary)
        self.marker_size = marker_size
        self.border_bits = border_bits
        self.generated_markers = []
        
        # Marker ID assignments - optimized for smaller markers
        self.corner_ids = {
            'CORNER_TL': 0,   # Top-Left
            'CORNER_TR': 1,   # Top-Right  
            'CORNER_BR': 2,   # Bottom-Right
            'CORNER_BL': 3    # Bottom-Left
        }
        
        self.player_id_range = (10, 25)  # IDs 10-25 for 16 players
        self.item_id_range = (30, 61)    # IDs 30-61 for 32 common items
        
        # Common tabletop gaming items
        self.standard_items = [
            {"id": 30, "name": "Goblin", "description": "Basic enemy - Goblin warrior"},
            {"id": 31, "name": "Orc", "description": "Medium enemy - Orc fighter"},
            {"id": 32, "name": "Skeleton", "description": "Undead enemy - Animated skeleton"},
            {"id": 33, "name": "Dragon", "description": "Boss enemy - Adult dragon"},
            {"id": 34, "name": "Troll", "description": "Large enemy - Cave troll"},
            {"id": 35, "name": "Wizard_Enemy", "description": "Spellcaster enemy - Evil wizard"},
            {"id": 36, "name": "Beast", "description": "Animal enemy - Dire wolf or bear"},
            {"id": 37, "name": "Demon", "description": "Fiend enemy - Lesser demon"},
            
            {"id": 40, "name": "Treasure_Chest", "description": "Loot container - Treasure chest"},
            {"id": 41, "name": "Magic_Item", "description": "Magical artifact - Enchanted object"},
            {"id": 42, "name": "Gold_Pile", "description": "Currency - Pile of gold coins"},
            {"id": 43, "name": "Potion", "description": "Consumable - Healing or magic potion"},
            {"id": 44, "name": "Weapon", "description": "Equipment - Sword, axe, or weapon"},
            {"id": 45, "name": "Armor", "description": "Equipment - Shield, armor piece"},
            {"id": 46, "name": "Scroll", "description": "Spell scroll - Magic document"},
            {"id": 47, "name": "Key", "description": "Quest item - Door or chest key"},
            
            {"id": 50, "name": "NPC_Merchant", "description": "Friendly NPC - Traveling merchant"},
            {"id": 51, "name": "NPC_Guard", "description": "Neutral NPC - Town guard"},
            {"id": 52, "name": "NPC_Noble", "description": "Important NPC - Lord or lady"},
            {"id": 53, "name": "NPC_Innkeeper", "description": "Service NPC - Tavern keeper"},
            {"id": 54, "name": "NPC_Priest", "description": "Religious NPC - Temple cleric"},
            
            {"id": 55, "name": "Door", "description": "Barrier - Wooden or stone door"},
            {"id": 56, "name": "Trap", "description": "Hidden danger - Pressure plate trap"},
            {"id": 57, "name": "Fire_Hazard", "description": "Environmental - Lava pit or flames"},
            {"id": 58, "name": "Altar", "description": "Religious site - Temple altar"},
            {"id": 59, "name": "Portal", "description": "Magical transport - Teleportation gate"},
            {"id": 60, "name": "Vehicle", "description": "Transportation - Cart, boat, or mount"},
            {"id": 61, "name": "Objective", "description": "Quest goal - Mission objective marker"}
        ]
    
    def generate_marker(self, marker_id: int) -> np.ndarray:
        """Generate a single ArUco marker."""
        marker_image = cv2.aruco.generateImageMarker(
            self.dictionary, marker_id, self.marker_size, borderBits=self.border_bits)
        return marker_image
    
    def create_labeled_marker(self, marker_id: int, label: str, 
                             description: str = "") -> np.ndarray:
        """Create a marker with label and description for printing."""
        marker = self.generate_marker(marker_id)
        
        # Convert to RGB for PIL
        marker_rgb = cv2.cvtColor(marker, cv2.COLOR_GRAY2RGB)
        
        # Create a larger image with space for labels
        label_height = 100
        total_height = self.marker_size + label_height
        labeled_image = np.ones((total_height, self.marker_size, 3), dtype=np.uint8) * 255
        
        # Place marker in the image
        labeled_image[0:self.marker_size, 0:self.marker_size] = marker_rgb
        
        # Convert to PIL for text rendering
        pil_image = Image.fromarray(labeled_image)
        draw = ImageDraw.Draw(pil_image)
        
        try:
            # Try to use a nice font
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            # Fallback to default font
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        # Draw label
        text_y = self.marker_size + 10
        draw.text((10, text_y), f"ID: {marker_id}", fill=(0, 0, 0), font=font_large)
        draw.text((10, text_y + 25), label, fill=(0, 0, 0), font=font_large)
        
        if description:
            draw.text((10, text_y + 50), description, fill=(100, 100, 100), font=font_small)
        
        # Convert back to numpy array
        return np.array(pil_image)
    
    def generate_corner_markers(self, output_dir: Path) -> List[Dict]:
        """Generate corner calibration markers."""
        print("Generating corner calibration markers...")
        corner_markers = []
        
        descriptions = {
            'CORNER_TL': 'Place at top-left corner of play area',
            'CORNER_TR': 'Place at top-right corner of play area', 
            'CORNER_BR': 'Place at bottom-right corner of play area',
            'CORNER_BL': 'Place at bottom-left corner of play area'
        }
        
        for corner_name, marker_id in self.corner_ids.items():
            # Generate labeled marker
            labeled_marker = self.create_labeled_marker(
                marker_id, corner_name, descriptions[corner_name])
            
            # Save individual marker
            filename = f"corner_{corner_name.lower()}_id{marker_id:03d}.png"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), cv2.cvtColor(labeled_marker, cv2.COLOR_RGB2BGR))
            
            marker_info = {
                'id': marker_id,
                'name': corner_name,
                'type': 'corner',
                'description': descriptions[corner_name],
                'filename': filename
            }
            corner_markers.append(marker_info)
            
            print(f"  Created {corner_name} (ID: {marker_id}) -> {filename}")
        
        return corner_markers
    
    def generate_player_markers(self, output_dir: Path, count: int = 16) -> List[Dict]:
        """Generate player token markers."""
        print(f"Generating {count} player markers...")
        player_markers = []
        
        start_id, end_id = self.player_id_range
        max_players = end_id - start_id + 1
        
        if count > max_players:
            print(f"Warning: Requested {count} players, but max is {max_players}. Generating {max_players} players.")
            count = max_players
        
        for i in range(count):
            marker_id = start_id + i
            player_name = f"PLAYER_{i+1:02d}"
            description = f"Player token #{i+1}"
            
            # Generate labeled marker
            labeled_marker = self.create_labeled_marker(marker_id, player_name, description)
            
            # Save individual marker
            filename = f"player_{i+1:02d}_id{marker_id:03d}.png"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), cv2.cvtColor(labeled_marker, cv2.COLOR_RGB2BGR))
            
            marker_info = {
                'id': marker_id,
                'name': player_name,
                'type': 'player',
                'description': description,
                'filename': filename
            }
            player_markers.append(marker_info)
            
            print(f"  Created {player_name} (ID: {marker_id}) -> {filename}")
        
        return player_markers
    
    def generate_standard_items(self, output_dir: Path) -> List[Dict]:
        """Generate standard tabletop gaming item markers."""
        print("Generating standard item markers...")
        item_markers = []
        
        for item_spec in self.standard_items:
            marker_id = item_spec['id']
            name = item_spec['name']
            description = item_spec['description']
            
            # Generate labeled marker
            labeled_marker = self.create_labeled_marker(marker_id, name, description)
            
            # Save individual marker
            filename = f"item_{name.lower()}_id{marker_id:03d}.png"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), cv2.cvtColor(labeled_marker, cv2.COLOR_RGB2BGR))
            
            marker_info = {
                'id': marker_id,
                'name': name,
                'type': 'item',
                'description': description,
                'filename': filename
            }
            item_markers.append(marker_info)
            
            print(f"  Created {name} (ID: {marker_id}) -> {filename}")
        
        return item_markers
    
    def generate_complete_set(self, output_dir: Path) -> Dict[str, List[Dict]]:
        """Generate complete set of markers: corners, all players, and all standard items."""
        print("=" * 60)
        print("GENERATING COMPLETE ARUCO MARKER SET")
        print("=" * 60)
        print("This will create:")
        print("- 4 corner markers (IDs 0-3)")
        print("- 16 player markers (IDs 10-25)")
        print("- 32 standard item markers (IDs 30-61)")
        print("- Print-ready sheets for each category")
        print()
        
        all_markers = {
            'corners': [],
            'players': [],
            'items': []
        }
        
        # Generate all marker types
        all_markers['corners'] = self.generate_corner_markers(output_dir)
        all_markers['players'] = self.generate_player_markers(output_dir, 16)  # All 16 players
        all_markers['items'] = self.generate_standard_items(output_dir)
        
        return all_markers
    def generate_custom_markers(self, output_dir: Path, custom_specs: List[Dict]) -> List[Dict]:
        """Generate custom markers from specifications."""
        print("Generating custom markers...")
        custom_markers = []
        
        for spec in custom_specs:
            marker_id = spec['id']
            name = spec['name']
            description = spec.get('description', '')
            
            # Validate ID range
            if marker_id < 62:
                print(f"Warning: Custom marker ID {marker_id} conflicts with standard ranges. Use IDs 62+")
                continue
            
            # Generate labeled marker
            labeled_marker = self.create_labeled_marker(marker_id, name, description)
            
            # Save individual marker
            filename = f"custom_{name.lower().replace(' ', '_')}_id{marker_id:03d}.png"
            filepath = output_dir / filename
            cv2.imwrite(str(filepath), cv2.cvtColor(labeled_marker, cv2.COLOR_RGB2BGR))
            
            marker_info = {
                'id': marker_id,
                'name': name,
                'type': 'custom',
                'description': description,
                'filename': filename
            }
            custom_markers.append(marker_info)
            
            print(f"  Created {name} (ID: {marker_id}) -> {filename}")
        
        return custom_markers
    
    def create_print_sheet(self, markers: List[Dict], output_dir: Path, 
                          sheet_name: str, markers_per_row: int = 4) -> str:
        """Create a print sheet with multiple markers."""
        print(f"Creating print sheet: {sheet_name}")
        
        if not markers:
            return None
        
        # Calculate sheet dimensions
        marker_width = self.marker_size
        marker_height = self.marker_size + 100  # Include label space
        margin = 20
        
        rows = (len(markers) + markers_per_row - 1) // markers_per_row
        sheet_width = markers_per_row * marker_width + (markers_per_row + 1) * margin
        sheet_height = rows * marker_height + (rows + 1) * margin
        
        # Create white sheet
        sheet = np.ones((sheet_height, sheet_width, 3), dtype=np.uint8) * 255
        
        # Place markers on sheet
        for i, marker_info in enumerate(markers):
            row = i // markers_per_row
            col = i % markers_per_row
            
            # Load marker image
            marker_path = output_dir / marker_info['filename']
            marker_img = cv2.imread(str(marker_path))
            marker_img = cv2.cvtColor(marker_img, cv2.COLOR_BGR2RGB)
            
            # Calculate position
            x = margin + col * (marker_width + margin)
            y = margin + row * (marker_height + margin)
            
            # Place marker
            sheet[y:y+marker_height, x:x+marker_width] = marker_img
        
        # Add sheet title
        pil_sheet = Image.fromarray(sheet)
        draw = ImageDraw.Draw(pil_sheet)
        
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
        except:
            title_font = ImageFont.load_default()
        
        title_text = f"ArUco Markers - {sheet_name}"
        draw.text((margin, 10), title_text, fill=(0, 0, 0), font=title_font)
        
        # Save sheet
        sheet_filename = f"print_sheet_{sheet_name.lower().replace(' ', '_')}.png"
        sheet_path = output_dir / sheet_filename
        pil_sheet.save(str(sheet_path))
        
        print(f"  Created print sheet: {sheet_filename}")
        return sheet_filename
    
    def save_marker_database(self, output_dir: Path, all_markers: List[Dict]):
        """Save marker database as JSON for reference."""
        database = {
            'generator_info': {
                'dictionary': 'DICT_6X6_250',
                'marker_size': self.marker_size,
                'border_bits': self.border_bits,
                'generated_date': str(Path().cwd())  # Simple timestamp
            },
            'id_schema': {
                'corner_markers': '0-3 (calibration)',
                'player_markers': f"{self.player_id_range[0]}-{self.player_id_range[1]} (16 players)",
                'item_markers': f"{self.item_id_range[0]}-{self.item_id_range[1]} (32 standard items)",
                'custom_markers': '62+ (user defined)'
            },
            'optimization': {
                'total_standard_markers': 4 + 16 + 32,
                'smaller_dictionary_compatible': True,
                'recommended_min_size': '15mm x 15mm'
            },
            'standard_items': self.standard_items,
            'markers': all_markers
        }
        
        db_path = output_dir / 'marker_database.json'
        with open(db_path, 'w') as f:
            json.dump(database, f, indent=2)
        
        print(f"Saved marker database: {db_path}")
        
        # Also save a quick reference
        ref_path = output_dir / 'quick_reference.txt'
        with open(ref_path, 'w') as f:
            f.write("ArUco Marker Quick Reference\n")
            f.write("==========================\n\n")
            f.write("CORNER MARKERS (Calibration):\n")
            f.write("ID 0: Top-Left corner\n")
            f.write("ID 1: Top-Right corner\n")
            f.write("ID 2: Bottom-Right corner\n")
            f.write("ID 3: Bottom-Left corner\n\n")
            f.write("PLAYER MARKERS (16 total):\n")
            for i in range(16):
                f.write(f"ID {10+i}: Player {i+1:02d}\n")
            f.write("\nSTANDARD ITEMS (32 total):\n")
            for item in self.standard_items:
                f.write(f"ID {item['id']}: {item['name']} - {item['description']}\n")
            f.write("\nCUSTOM MARKERS:\n")
            f.write("IDs 62+ available for custom use\n")
        
        print(f"Saved quick reference: {ref_path}")
    
    def generate_detection_reference(self, output_dir: Path):
        """Generate reference code for ArUco detection."""
        reference_code = f'''
# ArUco Detection Reference Code - Optimized Schema with OpenCV Compatibility
# ==========================================================================

import cv2
import numpy as np

# Initialize detector with backward compatibility
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters()

# Check OpenCV version for detector initialization
opencv_version = cv2.__version__
opencv_major = int(opencv_version.split('.')[0])
opencv_minor = int(opencv_version.split('.')[1])

# Determine which API to use
if opencv_major > 4 or (opencv_major == 4 and opencv_minor >= 7):
    try:
        detector = cv2.aruco.ArucoDetector(dictionary, parameters)
        use_new_api = True
        print(f"Using new ArUco API (OpenCV {{opencv_version}})")
    except AttributeError:
        detector = None
        use_new_api = False
        print(f"Falling back to legacy ArUco API (OpenCV {{opencv_version}})")
else:
    detector = None
    use_new_api = False
    print(f"Using legacy ArUco API (OpenCV {{opencv_version}})")

# Optimized ID ranges for smaller markers
CORNER_IDS = [0, 1, 2, 3]
PLAYER_ID_RANGE = ({self.player_id_range[0]}, {self.player_id_range[1]})  # 16 players
ITEM_ID_RANGE = ({self.item_id_range[0]}, {self.item_id_range[1]})      # 32 standard items

# Detect markers in frame
def detect_aruco_markers(frame):
    """Detect ArUco markers and return corners, ids, and rejected candidates."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # Use appropriate API based on OpenCV version
    if use_new_api and detector is not None:
        # New API (OpenCV 4.7+)
        corners, ids, rejected = detector.detectMarkers(gray)
    else:
        # Legacy API (OpenCV < 4.7)
        corners, ids, rejected = cv2.aruco.detectMarkers(
            gray, dictionary, parameters=parameters)
    
    detected_markers = []
    if ids is not None:
        for i, marker_id in enumerate(ids.flatten()):
            # Get marker corners
            marker_corners = corners[i][0]  # Shape: (4, 2)
            
            # Calculate center
            center_x = int(np.mean(marker_corners[:, 0]))
            center_y = int(np.mean(marker_corners[:, 1]))
            
            # Determine marker type
            if marker_id in CORNER_IDS:
                marker_type = 'corner'
            elif PLAYER_ID_RANGE[0] <= marker_id <= PLAYER_ID_RANGE[1]:
                marker_type = 'player'
            elif ITEM_ID_RANGE[0] <= marker_id <= ITEM_ID_RANGE[1]:
                marker_type = 'item'
            else:
                marker_type = 'custom'
            
            detected_markers.append({{
                'id': marker_id,
                'type': marker_type,
                'center': (center_x, center_y),
                'corners': marker_corners.tolist()
            }})
    
    return detected_markers

# Corner ID mapping
CORNER_MAPPING = {{
    0: 'CORNER_TL',  # Top-Left
    1: 'CORNER_TR',  # Top-Right
    2: 'CORNER_BR',  # Bottom-Right
    3: 'CORNER_BL'   # Bottom-Left
}}

# Standard item mapping
STANDARD_ITEMS = {{
'''
        
        for item in self.standard_items:
            reference_code += f"    {item['id']}: '{item['name']}',  # {item['description']}\n"
        
        reference_code += '''
}

# Helper functions
def get_player_number(marker_id):
    """Convert player marker ID to player number (1-16)."""
    if PLAYER_ID_RANGE[0] <= marker_id <= PLAYER_ID_RANGE[1]:
        return marker_id - PLAYER_ID_RANGE[0] + 1
    return None

def get_item_name(marker_id):
    """Get standard item name from marker ID."""
    return STANDARD_ITEMS.get(marker_id, f"Unknown_Item_{marker_id}")

# OpenCV version compatibility notes:
# - OpenCV 4.7+ uses cv2.aruco.ArucoDetector() class
# - OpenCV < 4.7 uses cv2.aruco.detectMarkers() function directly
# - This code automatically detects and uses the appropriate method
# - Raspberry Pi OS typically ships with OpenCV < 4.7
'''
        
        ref_path = output_dir / 'aruco_detection_reference.py'
        with open(ref_path, 'w') as f:
            f.write(reference_code)
        
        print(f"Generated detection reference: {ref_path}")


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(description="Generate ArUco markers for token tracking")
    parser.add_argument("--output-dir", default="aruco_markers", help="Output directory for markers")
    parser.add_argument("--marker-size", type=int, default=200, help="Marker size in pixels")
    parser.add_argument("--player-count", type=int, default=16, help="Number of player markers (max 16)")
    parser.add_argument("--complete", action="store_true", help="Generate complete set: corners + all 16 players + all 32 items")
    parser.add_argument("--corner-only", action="store_true", help="Generate only corner markers")
    parser.add_argument("--players-only", action="store_true", help="Generate only player markers")
    parser.add_argument("--items-only", action="store_true", help="Generate only standard item markers")
    parser.add_argument("--custom-file", help="JSON file with custom marker specifications (IDs 62+)")
    parser.add_argument("--no-sheets", action="store_true", help="Don't create print sheets")
    parser.add_argument("--markers-per-row", type=int, default=4, help="Markers per row in print sheets")
    
    args = parser.parse_args()
    
    # Validate player count
    if args.player_count > 16:
        print("Warning: Maximum 16 players supported. Setting to 16.")
        args.player_count = 16
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    print(f"ArUco Marker Generator - Optimized for Smaller Markers")
    print(f"======================================================")
    print(f"Output directory: {output_dir}")
    print(f"Marker size: {args.marker_size}px")
    print(f"Schema: Corners(0-3), Players(10-25), Items(30-61), Custom(62+)")
    print()
    
    # Initialize generator
    generator = ArucoMarkerGenerator(marker_size=args.marker_size)
    all_markers = []
    
    # Handle complete set generation
    if args.complete:
        print("GENERATING COMPLETE MARKER SET")
        print("=" * 50)
        marker_sets = generator.generate_complete_set(output_dir)
        
        # Flatten all markers for database
        all_markers.extend(marker_sets['corners'])
        all_markers.extend(marker_sets['players'])
        all_markers.extend(marker_sets['items'])
        
        # Create category-specific print sheets
        if not args.no_sheets:
            generator.create_print_sheet(marker_sets['corners'], output_dir, "Corner Markers", 2)
            generator.create_print_sheet(marker_sets['players'], output_dir, "Player Markers", args.markers_per_row)
            generator.create_print_sheet(marker_sets['items'], output_dir, "Item Markers", args.markers_per_row)
    
    else:
        # Generate individual categories
        if not args.players_only and not args.items_only:
            corner_markers = generator.generate_corner_markers(output_dir)
            all_markers.extend(corner_markers)
            
            if not args.no_sheets:
                generator.create_print_sheet(corner_markers, output_dir, "Corner Markers", 2)
        
        if not args.corner_only and not args.items_only:
            player_markers = generator.generate_player_markers(output_dir, args.player_count)
            all_markers.extend(player_markers)
            
            if not args.no_sheets:
                generator.create_print_sheet(player_markers, output_dir, "Player Markers", args.markers_per_row)
        
        if args.items_only or (not args.corner_only and not args.players_only):
            item_markers = generator.generate_standard_items(output_dir)
            all_markers.extend(item_markers)
            
            if not args.no_sheets:
                generator.create_print_sheet(item_markers, output_dir, "Item Markers", args.markers_per_row)
    
    # Generate custom markers if specified
    custom_markers = []
    if args.custom_file:
        try:
            with open(args.custom_file, 'r') as f:
                custom_specs = json.load(f)
            custom_markers = generator.generate_custom_markers(output_dir, custom_specs)
            all_markers.extend(custom_markers)
            
            if not args.no_sheets and custom_markers:
                generator.create_print_sheet(custom_markers, output_dir, "Custom Markers", args.markers_per_row)
        except Exception as e:
            print(f"Error loading custom markers: {e}")
    
    # Save marker database and reference
    generator.save_marker_database(output_dir, all_markers)
    generator.generate_detection_reference(output_dir)
    
    print()
    print("Generation complete!")
    print(f"Generated {len(all_markers)} markers total:")
    print(f"  - Corner markers: {len([m for m in all_markers if m['type'] == 'corner'])}")
    print(f"  - Player markers: {len([m for m in all_markers if m['type'] == 'player'])}")
    print(f"  - Item markers: {len([m for m in all_markers if m['type'] == 'item'])}")
    print(f"  - Custom markers: {len([m for m in all_markers if m['type'] == 'custom'])}")
    print()
    print("Optimizations for smaller markers:")
    print(f"  ✓ Total standard IDs used: {4 + 16 + 32} (0-61)")
    print(f"  ✓ Minimum recommended size: 15mm x 15mm")
    print(f"  ✓ Compatible with smaller ArUco dictionaries")
    print()
    print("Files created:")
    print(f"  - Individual markers: {len(all_markers)} PNG files")
    if not args.no_sheets:
        print(f"  - Print sheets: Ready-to-print layouts")
    print(f"  - marker_database.json: Complete marker reference")
    print(f"  - quick_reference.txt: Human-readable marker list")
    print(f"  - aruco_detection_reference.py: Detection code example")
    print()
    if args.complete:
        print("COMPLETE SET GENERATED! 🎉")
        print("You now have everything needed for tabletop gaming:")
        print("  ✓ 4 corner markers for calibration")
        print("  ✓ 16 player markers for party members")
        print("  ✓ 32 item markers for common game elements")
        print()
    print("Next steps:")
    print("1. Print the markers on white paper/cardstock")
    print("2. Cut out and mount on tokens/stands")
    print("3. Update your tracking code to use the new ID schema")
    print("4. Place corner markers and calibrate your system")


if __name__ == "__main__":
    main()
