# Quick Installation Guide

This guide gets you up and running with the ArUco Token Tracker in just a few steps.

## 🚀 One-Command Installation

```bash
# Make the install script executable and run it
chmod +x install_dependencies.sh
./install_dependencies.sh
```

This script automatically:
- ✅ Detects your system (Raspberry Pi, Ubuntu, etc.)
- ✅ Installs required system packages
- ✅ Installs Python dependencies
- ✅ Enables camera interface (Raspberry Pi)
- ✅ Tests the installation

## 📋 Manual Installation

If you prefer manual installation or the script has issues:

### 1. System Packages (Raspberry Pi)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-opencv python3-numpy python3-pil libcamera-dev python3-picamera2
sudo raspi-config nonint do_camera 0  # Enable camera
sudo usermod -a -G video $USER        # Add to video group
```

### 2. System Packages (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install python3 python3-pip python3-opencv python3-numpy python3-pil libopencv-dev
```

### 3. Python Dependencies
```bash
pip3 install -r requirements.txt
```

## 🔧 Alternative Installation Methods

### Option 1: System Packages Only (Raspberry Pi)
```bash
sudo apt install python3-opencv python3-numpy python3-pil python3-picamera2 python3-websockets python3-requests
```

### Option 2: Virtual Environment
```bash
python3 -m venv aruco_env
source aruco_env/bin/activate
pip install -r requirements.txt
```

### Option 3: User Installation
```bash
pip3 install --user -r requirements.txt
```

## 🧪 Test Your Installation

```bash
# Test core packages and check OpenCV compatibility
python3 check_opencv.py

# Test camera (Raspberry Pi only)
python3 -c "from picamera2 import Picamera2; print('✅ Camera OK')"

# Quick test of all components
python3 -c "
import cv2, numpy, websockets, requests
print(f'✅ OpenCV {cv2.__version__}')
print('✅ All packages OK')
"
```

## 🔧 OpenCV Version Compatibility

**Important**: The ArUco API changed in OpenCV 4.7+, but this code supports both versions automatically.

**Detection Functions:**
- **OpenCV < 4.7** (common on Raspberry Pi OS): Uses legacy `cv2.aruco.detectMarkers()` function
- **OpenCV 4.7+**: Uses new `cv2.aruco.ArucoDetector()` class

**Marker Generation Functions:**
- **OpenCV < 4.7**: Uses `cv2.aruco.drawMarker()` function (draws onto existing image)
- **OpenCV 4.7+**: Uses `cv2.aruco.generateImageMarker()` function (creates new image)

**Auto-detection**: The code automatically detects your version and uses the appropriate APIs for both detection and generation.

### Check Your OpenCV Version
```bash
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}')"
```

### If You Have Issues
```bash
# Check compatibility for both detection and generation
python3 check_opencv.py

# Force specific version (if needed)
pip3 install opencv-python==4.5.5.64
```

## 🚦 Quick Start After Installation

### 1. Generate Markers
```bash
python3 aruco_generator.py --complete
```
This creates 52 markers: 4 corners + 16 players + 32 items

### 2. Test Camera
```bash
python3 aruco_preview.py --fps 2.0
```
Place printed corner markers to test detection

### 3. Start Tracking
```bash
python3 foundry_aruco_tracker.py \
  --foundry-url "http://YOUR_FOUNDRY_IP:30000" \
  --scene-id "YOUR_SCENE_ID"
```

## 🔍 Troubleshooting

### OpenCV Issues
```bash
# Check your OpenCV version and API compatibility
python3 check_opencv.py

# If opencv-python fails, try headless version
pip3 install opencv-python-headless

# Use specific version for Raspberry Pi compatibility
pip3 install opencv-python==4.5.5.64

# If ArUco is missing (rare with modern OpenCV)
pip3 install opencv-contrib-python
```

### ArUco API Compatibility
The code automatically handles both OpenCV versions:
- **Legacy Detection API** (OpenCV < 4.7): `cv2.aruco.detectMarkers()`  
- **New Detection API** (OpenCV 4.7+): `cv2.aruco.ArucoDetector()`
- **Legacy Generation API** (OpenCV < 4.7): `cv2.aruco.drawMarker()`
- **New Generation API** (OpenCV 4.7+): `cv2.aruco.generateImageMarker()`

If you get `AttributeError: module 'cv2.aruco' has no attribute 'ArucoDetector'` or `AttributeError: module 'cv2.aruco' has no attribute 'generateImageMarker'`, this is normal for older OpenCV versions and the code will automatically fall back to the legacy APIs.

### Camera Permission Issues
```bash
# Add user to video group
sudo usermod -a -G video $USER

# Check camera is detected
ls /dev/video*

# Test camera manually
libcamera-hello --timeout 2000
```

### Import Errors
```bash
# Check installed packages
pip3 list | grep -E "(opencv|numpy|websockets|requests|picamera2)"

# Reinstall problematic package
pip3 install --force-reinstall package_name
```

### Network Issues
```bash
# Test network connectivity
python3 network_test.py --foundry-host YOUR_FOUNDRY_IP
```

### Dependency Conflicts
```bash
# Create clean virtual environment
python3 -m venv clean_env
source clean_env/bin/activate
pip install -r requirements.txt
```

## 📱 System-Specific Notes

### Raspberry Pi OS (Recommended)
- Use system packages when possible (faster, more stable)
- Enable camera interface via `raspi-config`
- Ensure adequate power supply (3A+ recommended)
- Use Class 10 SD card for better performance

### Ubuntu/Debian
- May need additional development packages
- Camera support varies by hardware
- Consider using USB camera if built-in camera not supported

### Other Systems
- Install OpenCV development libraries
- May need to compile some packages from source
- Check camera compatibility with your OS

## 🎯 Minimum System Requirements

### Raspberry Pi (Recommended)
- **Model**: Raspberry Pi 4B (2GB+ RAM)
- **OS**: Raspberry Pi OS (64-bit preferred)
- **Camera**: Official Raspberry Pi camera module
- **Storage**: 16GB+ SD card (Class 10)
- **Power**: 3A USB-C power supply

### Alternative Systems
- **CPU**: ARM64 or x64 processor
- **RAM**: 2GB+ (4GB+ recommended)
- **OS**: Linux-based (Ubuntu 20.04+, Debian 11+)
- **Camera**: USB camera or integrated camera
- **Python**: 3.7+ (3.9+ recommended)

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: Look for error messages during installation
2. **Test step-by-step**: Use the individual test commands above
3. **Check requirements**: Ensure your system meets minimum requirements
4. **Update system**: `sudo apt update && sudo apt upgrade`
5. **Clean install**: Try in a fresh virtual environment

### Common Error Solutions

**"AttributeError: module 'cv2.aruco' has no attribute 'ArucoDetector'"**
**"AttributeError: module 'cv2.aruco' has no attribute 'generateImageMarker'"**
```bash
# These are normal for OpenCV < 4.7 (common on Raspberry Pi)
# The code automatically uses legacy APIs - no action needed
python3 check_opencv.py  # Verify compatibility
```

**"ModuleNotFoundError: No module named 'cv2'"**
```bash
pip3 install opencv-python-headless
```

**"Permission denied" for camera**
```bash
sudo usermod -a -G video $USER
# Logout and login again
```

**"Failed to import picamera2"**
```bash
sudo apt install python3-picamera2
```

**WebSocket connection failed**
```bash
# Check firewall
sudo ufw allow 30001
```

## ✅ Success Checklist

After successful installation, you should be able to:
- [ ] Import all Python packages without errors
- [ ] Access the camera (on Raspberry Pi)
- [ ] Detect ArUco markers in camera preview
- [ ] Generate and print marker sheets
- [ ] Connect to Foundry VTT via network

When all items are checked, you're ready to start gaming with physical token tracking! 🎲🎮
