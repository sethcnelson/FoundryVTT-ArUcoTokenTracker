#!/bin/bash
"""
ArUco Camera Preview Launcher
============================

Quick launcher script for the ArUco camera preview tool with common configurations.

Usage:
    ./camera_launcher.sh [preset]

Presets:
    setup    - Setup mode: 5 FPS, help on, good for camera positioning and marker testing
    monitor  - Monitor mode: 10 FPS, minimal UI, optimized for game monitoring  
    debug    - Debug mode: 1 FPS, all overlays, save frames enabled
    fullscreen - Fullscreen mode for wall displays
    generate - Generate ArUco markers first, then preview
    custom   - Prompts for custom settings
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  ArUco Camera Preview Launcher${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_aruco() {
    echo -e "${MAGENTA}[ARUCO]${NC} $1"
}

# Check prerequisites and provide installation guidance
check_prerequisites() {
    if [ ! -f "aruco_camera.py" ]; then
        print_error "aruco_camera.py not found in current directory!"
        echo "Please ensure you're running this script from the directory containing aruco_camera.py"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found! Please install Python 3."
        echo "On Raspberry Pi: sudo apt install python3"
        exit 1
    fi
    
    # Check for required Python packages
    missing_packages=()
    
    if ! python3 -c "import cv2" 2>/dev/null; then
        missing_packages+=("opencv-python")
    fi
    
    if ! python3 -c "import numpy" 2>/dev/null; then
        missing_packages+=("numpy")
    fi
    
    if ! python3 -c "from picamera2 import Picamera2" 2>/dev/null; then
        missing_packages+=("picamera2")
    fi
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_error "Missing required packages: ${missing_packages[*]}"
        echo ""
        echo "Quick fix options:"
        echo "1. Run the automated installer:"
        echo "   chmod +x install_dependencies.sh && ./install_dependencies.sh"
        echo ""
        echo "2. Install manually:"
        echo "   pip3 install -r requirements.txt"
        echo ""
        echo "3. On Raspberry Pi, use system packages:"
        echo "   sudo apt install python3-opencv python3-numpy python3-picamera2"
        echo ""
        exit 1
    fi
    
    # Check for OpenCV ArUco support
    if ! python3 -c "import cv2; cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)" 2>/dev/null; then
        print_error "OpenCV ArUco support not found!"
        echo "Try: pip3 install opencv-contrib-python"
        exit 1
    fi
    
    print_status "All prerequisites satisfied ✓"
    print_aruco "ArUco DICT_6X6_250 dictionary available ✓"
}

# Generate ArUco markers
generate_markers() {
    print_aruco "Checking for ArUco marker generator..."
    
    if [ ! -f "aruco_generator.py" ]; then
        print_warning "aruco_generator.py not found. Skipping marker generation."
        return 1
    fi
    
    print_aruco "Generating ArUco markers..."
    echo ""
    echo "Quick marker generation options:"
    echo "  1) Basic set (4 corners + 10 players)"
    echo "  2) Full set (4 corners + 20 players)"
    echo "  3) Corner markers only"
    echo "  4) Skip generation"
    echo -n "Choose option (1-4, default 1): "
    read gen_choice
    
    case $gen_choice in
        2)
            print_aruco "Generating full marker set..."
            python3 aruco_generator.py --output-dir aruco_markers --player-count 20
            ;;
        3)
            print_aruco "Generating corner markers only..."
            python3 aruco_generator.py --output-dir aruco_markers --corner-only
            ;;
        4)
            print_status "Skipping marker generation"
            return 0
            ;;
        *)
            print_aruco "Generating basic marker set..."
            python3 aruco_generator.py --output-dir aruco_markers --player-count 10
            ;;
    esac
    
    if [ $? -eq 0 ]; then
        print_status "Markers generated successfully!"
        echo "Check the 'aruco_markers' directory for print-ready files."
        echo ""
    else
        print_error "Marker generation failed!"
        return 1
    fi
}

# Setup mode: Good for initial camera positioning and calibration
launch_setup() {
    print_status "Starting SETUP mode..."
    print_status "- 5 FPS for smooth setup"
    print_status "- Help overlay enabled"
    print_status "- All detection enabled"
    print_status "- Optimized for camera positioning and ArUco testing"
    print_aruco "Place corner markers (IDs 0-3) at table corners"
    echo ""
    python3 aruco_camera.py --fps 5 --resolution 1280x720
}

# Monitor mode: Minimal UI for game monitoring
launch_monitor() {
    print_status "Starting MONITOR mode..."
    print_status "- 10 FPS for smooth monitoring"
    print_status "- Help overlay disabled"
    print_status "- Focus on player tokens"
    print_aruco "Tracking player markers (IDs 10-99) and custom markers (100+)"
    echo ""
    python3 aruco_camera.py --fps 10 --resolution 1920x1080 --no-help
}

# Debug mode: All features enabled, saves frames
launch_debug() {
    print_status "Starting DEBUG mode..."
    print_status "- 1 FPS with all overlays"
    print_status "- All detection enabled"
    print_status "- Press 's' to save frames for debugging"
    print_aruco "Perfect for troubleshooting ArUco detection issues"
    echo ""
    python3 aruco_camera.py --fps 1.0 --resolution 1280x720
}

# Fullscreen mode: For wall displays or projectors
launch_fullscreen() {
    print_status "Starting FULLSCREEN mode..."
    print_status "- 10 FPS optimized for display"
    print_status "- Fullscreen mode enabled"
    print_status "- Press 'f' to exit fullscreen"
    print_aruco "Great for demonstrating ArUco tracking to others"
    echo ""
    python3 aruco_camera.py --fps 10 --resolution 1920x1080 --fullscreen --no-help
}

# Generate and preview mode
launch_generate() {
    print_status "Starting GENERATE & PREVIEW mode..."
    
    # First generate markers
    if generate_markers; then
        echo ""
        print_status "Now starting preview to test the generated markers..."
        echo "Place the printed corner markers (IDs 0-3) at your table corners"
        echo "Then test player markers within the bounded area"
        echo ""
        sleep 3
        python3 aruco_camera.py --fps 2.0 --resolution 1280x720
    else
        print_warning "Marker generation had issues, but starting preview anyway..."
        python3 aruco_camera.py --fps 2.0 --resolution 1280x720
    fi
}

# Custom mode: Interactive configuration
launch_custom() {
    print_status "Starting CUSTOM configuration..."
    echo ""
    
    # Get FPS
    echo -n "Enter FPS (1-30, default 2.0 for ArUco): "
    read fps_input
    fps=${fps_input:-2.0}
    
    # Get resolution
    echo "Available resolutions:"
    echo "  1) 640x480   (Low - good for older Pis)"
    echo "  2) 1280x720  (HD - Default, recommended)"
    echo "  3) 1920x1080 (Full HD - for capable setups)"
    echo "  4) 2592x1944 (HD+ - for powerful setups)"
    echo "  5) Custom"
    echo -n "Choose resolution (1-5, default 2): "
    read res_choice
    
    case $res_choice in
        1) resolution="640x480" ;;
        2) resolution="1280x720" ;;
        3) resolution="1920x1080" ;;
        4) resolution="2592x1944" ;;
        5) 
            echo -n "Enter custom resolution (WIDTHxHEIGHT): "
            read resolution
            ;;
        *) resolution="1280x720" ;;
    esac
    
    # Additional options
    echo -n "Start in fullscreen? (y/n, default n): "
    read fullscreen_input
    fullscreen_flag=""
    if [[ $fullscreen_input == "y" || $fullscreen_input == "Y" ]]; then
        fullscreen_flag="--fullscreen"
    fi
    
    echo -n "Hide help overlay? (y/n, default n): "
    read no_help_input
    no_help_flag=""
    if [[ $no_help_input == "y" || $no_help_input == "Y" ]]; then
        no_help_flag="--no-help"
    fi
    
    echo -n "Disable corner detection? (y/n, default n): "
    read no_corners_input
    no_corners_flag=""
    if [[ $no_corners_input == "y" || $no_corners_input == "Y" ]]; then
        no_corners_flag="--no-corners"
    fi
    
    print_status "Starting with custom settings..."
    print_status "FPS: $fps, Resolution: $resolution"
    print_aruco "ArUco DICT_6X6_250 detection active"
    echo ""
    
    python3 aruco_camera.py --fps "$fps" --resolution "$resolution" $fullscreen_flag $no_help_flag $no_corners_flag
}

# Show usage information
show_usage() {
    print_header
    echo ""
    echo "Usage: $0 [preset]"
    echo ""
    echo "Available presets:"
    echo "  setup      - Setup mode: 5 FPS, help on, good for camera positioning"
    echo "  monitor    - Monitor mode: 10 FPS, minimal UI, optimized for gameplay"
    echo "  debug      - Debug mode: 1 FPS, all overlays, frame saving"
    echo "  fullscreen - Fullscreen mode for wall displays (1920x1080)"
    echo "  generate   - Generate ArUco markers, then start preview"
    echo "  custom     - Interactive custom configuration"
    echo ""
    echo "If no preset is specified, setup mode is used."
    echo ""
    echo "ArUco Marker Schema:"
    echo "  Corner markers: IDs 0-3 (TL=0, TR=1, BR=2, BL=3)"
    echo "  Player markers: IDs 10-99 (up to 90 players)"
    echo "  Custom markers: IDs 100+ (special tokens, NPCs, etc.)"
    echo ""
    echo "Controls during preview:"
    echo "  h - Toggle help overlay"
    echo "  c - Toggle corner detection"
    echo "  p - Toggle player detection"
    echo "  s - Save current frame"
    echo "  f - Toggle fullscreen"
    echo "  q - Quit"
    echo ""
    echo "ArUco Advantages:"
    echo "  ✓ 10x faster detection than QR codes"
    echo "  ✓ Works with smaller markers (1.5cm minimum)"
    echo "  ✓ Better performance in low light"
    echo "  ✓ More robust to viewing angles"
    echo "  ✓ Lower CPU usage on Raspberry Pi"
    echo ""
}

# Check for marker directory
check_markers() {
    if [ -d "aruco_markers" ]; then
        marker_count=$(find aruco_markers -name "*.png" | wc -l)
        if [ $marker_count -gt 0 ]; then
            print_aruco "Found $marker_count ArUco markers in aruco_markers/ directory"
            print_status "Markers are ready for printing and use"
        else
            print_warning "aruco_markers/ directory exists but contains no PNG files"
            echo "Run with 'generate' preset to create markers"
        fi
    else
        print_warning "No aruco_markers/ directory found"
        echo "Run with 'generate' preset to create markers first"
    fi
}

# Main script logic
main() {
    print_header
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
    # Check for existing markers
    check_markers
    echo ""
    
    # Get preset from command line argument
    preset=${1:-setup}
    
    case $preset in
        "setup")
            launch_setup
            ;;
        "monitor")
            launch_monitor
            ;;
        "debug")
            launch_debug
            ;;
        "fullscreen")
            launch_fullscreen
            ;;
        "generate")
            launch_generate
            ;;
        "custom")
            launch_custom
            ;;
        "help"|"-h"|"--help")
            show_usage
            exit 0
            ;;
        *)
            print_warning "Unknown preset: $preset"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Make sure script is executable and run main function
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi
