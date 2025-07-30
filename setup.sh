#!/bin/bash
"""
ArUco Token Tracker - Installation Script
=========================================

This script installs all dependencies for the ArUco token tracking system.
Run with: ./install_dependencies.sh

Supports:
- Raspberry Pi OS (recommended)
- Ubuntu/Debian systems
- Other Linux distributions
"""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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
    echo -e "${BLUE}  ArUco Tracker Installation${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Detect system type
detect_system() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    echo "Detected system: $OS $VER"
}

# Check if running on Raspberry Pi
is_raspberry_pi() {
    if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Install system packages for Raspberry Pi
install_system_packages_rpi() {
    print_status "Installing system packages for Raspberry Pi..."
    
    sudo apt update
    
    # Core packages
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-opencv \
        python3-numpy \
        python3-pil \
        libcamera-dev \
        python3-picamera2
    
    if [ $? -eq 0 ]; then
        print_status "System packages installed successfully!"
    else
        print_error "Failed to install system packages"
        return 1
    fi
    
    # Enable camera interface
    print_status "Enabling camera interface..."
    if command -v raspi-config >/dev/null 2>&1; then
        sudo raspi-config nonint do_camera 0
        print_status "Camera interface enabled"
    else
        print_warning "raspi-config not found. You may need to enable camera manually."
    fi
    
    # Add user to video group
    print_status "Adding user to video group..."
    sudo usermod -a -G video $USER
    print_warning "You'll need to logout and login again for group changes to take effect"
}

# Install system packages for Ubuntu/Debian
install_system_packages_debian() {
    print_status "Installing system packages for Ubuntu/Debian..."
    
    sudo apt update
    
    sudo apt install -y \
        python3 \
        python3-pip \
        python3-dev \
        python3-opencv \
        python3-numpy \
        python3-pil \
        libopencv-dev
    
    if [ $? -eq 0 ]; then
        print_status "System packages installed successfully!"
    else
        print_error "Failed to install system packages"
        return 1
    fi
}

# Install Python packages
install_python_packages() {
    print_status "Installing Python packages..."
    
    # Setup virtual environment for pip
    python3 -m venv aruco_env
	source aruco_env/bin/activate
    
    # Upgrade pip first
    pip install --upgrade pip
    
    # Install from requirements.txt if it exists
    if [ -f "dependencies.txt" ]; then
        print_status "Installing from dependencies.txt..."
        pip install -r dependencies.txt
    else
        # Manual installation
        print_status "Installing core packages manually..."
        
        # Core packages that should work on most systems
        pip install \
            numpy>=1.19.0 \
            Pillow>=8.0.0 \
            websockets>=10.0 \
            requests>=2.25.0
        
        # Try to install OpenCV (may fail on some systems)
        if ! python3 -c "import cv2" 2>/dev/null; then
            print_status "Installing OpenCV..."
            pip install opencv-python>=4.5.0
            
            if [ $? -ne 0 ]; then
                print_warning "OpenCV installation failed. Trying headless version..."
                pip install opencv-python-headless>=4.5.0
            fi
        else
            print_status "OpenCV already available (system package)"
        fi
        
        # Install picamera2 for Raspberry Pi
        if is_raspberry_pi; then
            if ! python3 -c "import picamera2" 2>/dev/null; then
                print_status "Installing picamera2..."
                pip install picamera2>=0.3.0
            else
                print_status "picamera2 already available (system package)"
            fi
        fi
    fi
    
    if [ $? -eq 0 ]; then
        print_status "Python packages installed successfully!"
    else
        print_error "Some Python packages failed to install"
        return 1
    fi
}

# Test installation
test_installation() {
    print_status "Testing installation..."
    
    # Test core imports and check OpenCV version
    python3 -c "
import sys
import traceback

packages = [
    ('numpy', 'NumPy'),
    ('PIL', 'Pillow'),
    ('websockets', 'WebSockets'),
    ('requests', 'Requests'),
]

# Add picamera2 test for Raspberry Pi
try:
    with open('/proc/cpuinfo', 'r') as f:
        if 'Raspberry Pi' in f.read():
            packages.append(('picamera2', 'PiCamera2'))
except:
    pass

failed = []
for package, name in packages:
    try:
        __import__(package)
        print(f'✓ {name}')
    except ImportError as e:
        print(f'✗ {name}: {e}')
        failed.append(name)
    except Exception as e:
        print(f'? {name}: {e}')
        failed.append(name)

# Special OpenCV test with version check
try:
    import cv2
    opencv_version = cv2.__version__
    print(f'✓ OpenCV: {opencv_version}')
    
    # Check ArUco support
    try:
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        print('✓ ArUco: Dictionary support available')
        
        # Check which API is available
        opencv_major = int(opencv_version.split('.')[0])
        opencv_minor = int(opencv_version.split('.')[1])
        
        if opencv_major > 4 or (opencv_major == 4 and opencv_minor >= 7):
            try:
                parameters = cv2.aruco.DetectorParameters()
                detector = cv2.aruco.ArucoDetector(dictionary, parameters)
                print('✓ ArUco: New API (4.7+) available')
            except AttributeError:
                print('✓ ArUco: Legacy API (<4.7) will be used')
        else:
            print('✓ ArUco: Legacy API (<4.7) will be used')
            
    except Exception as e:
        print(f'✗ ArUco: {e}')
        failed.append('ArUco')
        
except ImportError as e:
    print(f'✗ OpenCV: {e}')
    failed.append('OpenCV')
except Exception as e:
    print(f'? OpenCV: {e}')
    failed.append('OpenCV')

if failed:
    print(f'\nFailed packages: {failed}')
    print('\nCommon fixes:')
    if 'OpenCV' in failed:
        print('- Try: pip3 install opencv-python-headless')
        print('- Or: sudo apt install python3-opencv')
    if 'ArUco' in failed:
        print('- ArUco should be included with OpenCV 4.2+')
        print('- Try: pip3 install opencv-contrib-python')
    sys.exit(1)
else:
    print('\nAll packages imported successfully!')
"
    
    if [ $? -eq 0 ]; then
        print_status "Installation test passed!"
        return 0
    else
        print_error "Installation test failed!"
        return 1
    fi
}

# Show next steps
show_next_steps() {
    echo ""
    print_status "Installation complete! 🎉"
    echo ""
    echo "Next steps:"
    echo "1. Check OpenCV compatibility:"
    echo "   python3 check_opencv.py"
    echo ""
    echo "2. Generate ArUco markers:"
    echo "   python3 aruco_generator.py --complete"
    echo ""
    echo "3. Test camera and detection:"
    echo "   python3 aruco_preview.py"
    echo ""
    echo "4. Set up Foundry VTT module (see README)"
    echo ""
    echo "5. Start tracking:"
    echo "   python3 foundry_aruco_tracker.py --foundry-url http://your-foundry-ip:30000 --scene-id your-scene-id"
    echo ""
    
    if is_raspberry_pi; then
        print_warning "Important: Logout and login again for camera permissions to take effect"
        echo ""
        echo "Note: Raspberry Pi OS typically uses OpenCV < 4.7 with legacy ArUco API."
        echo "This is fully supported and detected automatically."
    fi
    
    echo ""
    echo "For troubleshooting, see the setup guide README."
}

# Main installation function
main() {
    print_header
    echo ""
    
    detect_system
    echo ""
    
    # Install system packages based on detected OS
    if is_raspberry_pi; then
        print_status "Installing for Raspberry Pi..."
        install_system_packages_rpi
    elif [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        print_status "Installing for Ubuntu/Debian..."
        install_system_packages_debian
    else
        print_warning "Unknown system. Attempting generic installation..."
        print_warning "You may need to install system packages manually:"
        echo "  - Python 3.7+"
        echo "  - OpenCV development libraries"
        echo "  - Camera drivers (for Raspberry Pi)"
        echo ""
    fi
    
    # Install Python packages
    install_python_packages
    
    echo ""
    
    # Test installation
    test_installation
    
    if [ $? -eq 0 ]; then
        show_next_steps
    else
        echo ""
        print_error "Installation completed with errors."
        echo "Check the messages above and refer to the troubleshooting guide."
        echo ""
        echo "Common solutions:"
        echo "- Try: pip3 install --user -r requirements.txt"
        echo "- For OpenCV issues: pip3 install opencv-python-headless"
        echo "- For permission issues: sudo usermod -a -G video \$USER"
        exit 1
    fi
}

# Run main function
main "$@"
