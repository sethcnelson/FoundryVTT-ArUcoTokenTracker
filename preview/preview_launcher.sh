#!/bin/bash
"""
QR Camera Preview Launcher
=========================

Quick launcher script for the QR camera preview tool with common configurations.

Usage:
    ./launch_preview.sh [preset]

Presets:
    setup    - Setup mode: 1 FPS, help on, good for initial camera positioning
    monitor  - Monitor mode: 2 FPS, minimal UI, good for game monitoring  
    debug    - Debug mode: 1 FPS, all overlays, save frames enabled
    fullscreen - Fullscreen mode for wall displays
    custom   - Prompts for custom settings
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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
    echo -e "${BLUE}  QR Camera Preview Launcher${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if camera_preview.py exists
check_prerequisites() {
    if [ ! -f "camera_preview.py" ]; then
        print_error "camera_preview.py not found in current directory!"
        echo "Please ensure you're running this script from the directory containing camera_preview.py"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "python3 not found! Please install Python 3."
        exit 1
    fi
    
    print_status "Prerequisites check passed"
}

# Setup mode: Good for initial camera positioning and calibration
launch_setup() {
    print_status "Starting SETUP mode..."
    print_status "- 1 FPS for efficiency"
    print_status "- Help overlay enabled"
    print_status "- All detection enabled"
    print_status "- Good for camera positioning and corner marker placement"
    echo ""
    python3 camera_preview.py --fps 1.0 --resolution 1280x720
}

# Monitor mode: Minimal UI for game monitoring
launch_monitor() {
    print_status "Starting MONITOR mode..."
    print_status "- 2 FPS for smoother monitoring"
    print_status "- Help overlay disabled"
    print_status "- Focus on player tokens"
    echo ""
    python3 camera_preview.py --fps 2.0 --resolution 1280x720 --no-help
}

# Debug mode: All features enabled, saves frames
launch_debug() {
    print_status "Starting DEBUG mode..."
    print_status "- 1 FPS with all overlays"
    print_status "- All detection enabled"
    print_status "- Press 's' to save frames for debugging"
    echo ""
    python3 camera_preview.py --fps 1.0 --resolution 1280x720
}

# Fullscreen mode: For wall displays or projectors
launch_fullscreen() {
    print_status "Starting FULLSCREEN mode..."
    print_status "- 2 FPS optimized for display"
    print_status "- Fullscreen mode enabled"
    print_status "- Press 'f' to exit fullscreen"
    echo ""
    python3 camera_preview.py --fps 2.0 --resolution 1920x1080 --fullscreen --no-help
}

# Custom mode: Interactive configuration
launch_custom() {
    print_status "Starting CUSTOM configuration..."
    echo ""
    
    # Get FPS
    echo -n "Enter FPS (0.5-5.0, default 1.0): "
    read fps_input
    fps=${fps_input:-1.0}
    
    # Get resolution
    echo "Available resolutions:"
    echo "  1) 640x480   (Low)"
    echo "  2) 1280x720  (HD - Default)"
    echo "  3) 1920x1080 (Full HD)"
    echo "  4) Custom"
    echo -n "Choose resolution (1-4, default 2): "
    read res_choice
    
    case $res_choice in
        1) resolution="640x480" ;;
        3) resolution="1920x1080" ;;
        4) 
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
    
    print_status "Starting with custom settings..."
    print_status "FPS: $fps, Resolution: $resolution"
    echo ""
    
    python3 camera_preview.py --fps "$fps" --resolution "$resolution" $fullscreen_flag $no_help_flag
}

# Show usage information
show_usage() {
    print_header
    echo ""
    echo "Usage: $0 [preset]"
    echo ""
    echo "Available presets:"
    echo "  setup      - Setup mode: 1 FPS, help on, good for camera positioning"
    echo "  monitor    - Monitor mode: 2 FPS, minimal UI, good for game monitoring"
    echo "  debug      - Debug mode: 1 FPS, all overlays, frame saving"
    echo "  fullscreen - Fullscreen mode for wall displays (1920x1080)"
    echo "  custom     - Interactive custom configuration"
    echo ""
    echo "If no preset is specified, setup mode is used."
    echo ""
    echo "Controls during preview:"
    echo "  h - Toggle help overlay"
    echo "  c - Toggle corner detection"
    echo "  p - Toggle player detection"
    echo "  s - Save current frame"
    echo "  f - Toggle fullscreen"
    echo "  q - Quit"
    echo ""
}

# Main script logic
main() {
    print_header
    echo ""
    
    # Check prerequisites
    check_prerequisites
    
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
