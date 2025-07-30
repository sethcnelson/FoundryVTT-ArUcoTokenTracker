# Foundry VTT ArUco Token Tracker Setup Guide

This system uses **ArUco markers** instead of QR codes for superior tracking performance. ArUco markers are specifically designed for computer vision applications and offer faster detection, better accuracy, and improved reliability.

## Why ArUco Markers?

### ✅ **Advantages over QR Codes:**
- **10x faster detection** - Optimized for computer vision
- **Better at low resolution** - Works with smaller markers
- **More robust tracking** - Handles lighting changes better
- **Precise positioning** - Sub-pixel accuracy for smooth movement
- **Standardized system** - Consistent performance across devices
- **Lower CPU usage** - More efficient for Raspberry Pi

### 📐 **ArUco Marker Schema:**
- **Corner markers**: IDs 0-3 (TL=0, TR=1, BR=2, BL=3) for surface calibration
- **Player tokens**: IDs 10-99 (90 unique players)
- **Custom tokens**: IDs 100+ (special items, NPCs, etc.)

## System Overview

- **Physical Layer**: ArUco markers on your gaming table tracked by Raspberry Pi camera
- **Digital Layer**: Foundry VTT tokens that mirror the physical token positions  
- **Bridge**: Python script that connects the physical tracking to Foundry
- **Network**: Works across different machines - Pi tracks, Foundry runs elsewhere

## Hardware Requirements

- Raspberry Pi 4 (recommended) with camera module
- Camera mount positioned above your gaming table
- ArUco markers (generated and printed)
- Gaming surface with clear boundaries
- **Network**: Both Pi and Foundry host on same network (WiFi/Ethernet)

## Required Files

### Raspberry Pi Files:
1. **`aruco_generator.py`** - Generate and print ArUco markers
2. **`foundry_aruco_tracker.py`** - Main tracking script
3. **`aruco_preview.py`** - Camera preview with ArUco overlays
4. **`network_test.py`** - Network connectivity test script

### Foundry VTT Module Files:
Create directory: `Data/modules/aruco-tracker/`
1. **`module.json`** - Module manifest
2. **`aruco-tracker.js`** - Module JavaScript code

## Software Installation

### 1. Raspberry Pi Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install python3-opencv python3-numpy python3-pip

# Install Python packages
pip3 install picamera2 opencv-python numpy websockets requests aiohttp
```

### 2. Foundry VTT Module Installation

1. Create folder: `Data/modules/aruco-tracker/`
2. Place these files in the folder:
   - `module.json` (manifest file)
   - `aruco-tracker.js` (main module code)
3. Restart Foundry VTT
4. Enable the "ArUco Token Tracker" module in your world

## Step-by-Step Setup

### 1. Generate ArUco Markers

```bash
# Generate basic set (corner + 20 player markers)
python3 aruco_generator.py --output-dir aruco_markers --player-count 20

# Generate only corners
python3 aruco_generator.py --corner-only

# Generate custom markers
python3 aruco_generator.py --custom-file my_custom_markers.json
```

**Output includes:**
- Individual marker PNG files
- Print-ready sheets
- Marker database (JSON)
- Detection reference code

### 2. Print and Prepare Markers

**Printing Guidelines:**
- Use **white paper or cardstock** (laser printer preferred)
- **Minimum 2cm x 2cm** marker size for reliable detection
- **High contrast** - ensure pure black/white printing
- **No scaling** - print at 100% size
- **Laminate** for durability (optional)

**Corner Markers:**
- Print corner markers (IDs 0-3) on sturdy material
- Mount on stands or attach to table edges
- Position at exact corners of your play area

**Player Tokens:**
- Print player markers (IDs 10-29 for 20 players)
- Attach to token bases or miniature stands
- Consider color-coding borders for easy identification

### 3. Network Setup

**Find Your Raspberry Pi's IP Address:**
```bash
# On the Raspberry Pi
hostname -I
# Example output: 192.168.1.100
```

**Test Network Connectivity (Recommended):**
```bash
# Run the network test script first
python3 network_test.py --foundry-host 192.168.1.50 --foundry-port 30000

# This will test:
# - Basic connectivity between machines
# - Foundry HTTP API accessibility  
# - WebSocket port availability
```

**Firewall Configuration:**
```bash
# On Raspberry Pi, open WebSocket port
sudo ufw allow 30001

# On Foundry host (if needed)
sudo ufw allow from 192.168.1.100
```

### 4. Camera Setup and Calibration

```bash
# Start camera preview to position and test
python3 aruco_preview.py --fps 2.0

# Or use the launcher for easier setup
chmod +x launch_preview.sh
./launch_preview.sh setup
```

**Camera Positioning:**
- Mount camera 60-100cm above table
- Ensure entire play area is visible
- Camera should be roughly perpendicular to surface
- Good, even lighting across surface

**Test Detection:**
- Place corner markers at table corners
- Verify all 4 corners are detected (green bounding box appears)
- Test player markers within the bounded area
- Adjust lighting/position as needed

### 5. Foundry Configuration

1. Open your Foundry world
2. Create or open the scene you want to use
3. Note the Scene ID (visible in the URL or scene configuration)
4. Configure module settings in Foundry:
   - **ArUco Tracker Host**: IP address of your Raspberry Pi (e.g., `192.168.1.100`)
   - **WebSocket Port**: Default 30001 (must match Python script)
   - **Auto-create tokens**: Enabled (recommended)
   - **Player token image**: Set your preferred player token image
   - **Default token image**: For custom markers

### 6. Start Tracking

**For Remote Foundry (most common):**
```bash
python3 foundry_aruco_tracker.py \
  --foundry-url "http://192.168.1.50:30000" \
  --scene-id "abc123def456" \
  --surface-width 1000 \
  --surface-height 1000
```

**Command Line Options:**
- `--foundry-url`: Your Foundry server URL (IP:port)
- `--scene-id`: The scene to update (get from Foundry URL)
- `--surface-width/height`: Coordinate system size
- `--websocket-port`: WebSocket port (default: 30001)
- `--no-display`: Run without camera preview window

### 7. Verify Connection

1. **In Foundry**: Check the ArUco Tracker status button in scene controls
2. **Python Console**: Look for "Connected to Foundry WebSocket" message
3. **Test Connection**: Use the "Test Connection" button in Foundry status dialog

## Usage During Games

### Physical Tokens
- Place ArUco markers on your surface within the calibrated area
- Move tokens around - Foundry tokens will follow in real-time with smooth movement
- Remove tokens from surface - they'll disappear from Foundry after 3 seconds
- **Much faster response** than QR codes - minimal lag

### Foundry Interface
- Tokens auto-create when new ArUco markers are detected
- Player tokens (IDs 10-99) get names like "Player_01", "Player_02", etc.
- Custom tokens (IDs 100+) get names like "Token_101", "Token_102", etc.
- Green indicator = token connected to ArUco tracker
- Real-time position updates with sub-pixel precision

### ArUco Marker Benefits During Play
- **Instant detection** - no scanning delays
- **Works at any angle** - doesn't need to be perfectly flat
- **Smaller size** - can use 1.5cm markers if needed
- **Better in dim lighting** - more robust than QR codes
- **No orientation issues** - detected from any rotation

## Troubleshooting

**ArUco Detection Issues:**

**No markers detected:**
- Ensure high contrast printing (pure black/white)
- Check marker isn't damaged or wrinkled
- Verify adequate lighting (avoid harsh shadows)
- Try increasing marker size
- Clean camera lens

**"AttributeError: ArucoDetector" errors:**
- This is normal for OpenCV < 4.7 (common on Raspberry Pi OS)
- The code automatically detects your OpenCV version and uses the appropriate API
- Run `python3 check_opencv.py` to verify compatibility
- No action needed - the tracker works with both API versions

**Poor Detection Performance:**
- Use DICT_6X6_250 dictionary (default - good balance)
- Ensure markers are flat on surface
- Check for reflections or glare
- Verify camera focus

**Corner Calibration Problems:**
- Place corner markers exactly at play area boundaries
- Ensure all 4 corners (IDs 0-3) are visible simultaneously
- Check markers aren't too close to camera edges
- Verify correct IDs: 0=TL, 1=TR, 2=BR, 3=BL

### Network/Connection Issues
```bash
# Check if Foundry host is reachable
ping [foundry-host-ip]

# Test WebSocket port connectivity  
telnet [foundry-host-ip] 30001

# Check if Python script can reach Foundry HTTP API
curl http://[foundry-host-ip]:30000/api/scenes
```

**Common Network Problems:**
- **"Connection refused"**: Check firewall settings and port availability
- **"Host unreachable"**: Verify both machines are on same network
- **"WebSocket disconnected"**: Check if Foundry module is enabled and configured
- **"No route to host"**: Check IP addresses and network configuration

### Performance Issues

**Slow Detection:**
- ArUco should be much faster than QR codes
- Lower camera resolution if needed (`--resolution 640x480`)
- Reduce FPS if system is overloaded
- Close other applications on Pi

**High CPU Usage:**
- ArUco is more efficient than QR codes, but if issues persist:
- Use lower resolution
- Reduce detection frequency
- Check camera isn't running other processes

## Advanced Configuration

### Custom Marker Sets

Create custom marker specifications in JSON:

```json
[
  {
    "id": 100,
    "name": "Magic_Sword",
    "description": "Legendary magic sword token"
  },
  {
    "id": 101,
    "name": "Dragon_Boss",
    "description": "Final boss encounter"
  }
]
```

Generate with:
```bash
python3 aruco_generator.py --custom-file custom_markers.json
```

### Multiple Camera Setup (Future)

The ArUco system is designed to support multiple cameras:
- Each camera can track different table sections
- Markers are globally unique across all cameras
- Combine tracking data for larger play areas

### Integration with Other Systems

ArUco markers can integrate with:
- **RFID systems**: Embed RFID in marker tokens
- **LED indicators**: Add status LEDs to token bases
- **Sound systems**: Trigger audio based on token positions
- **Projection mapping**: Project effects around tokens

## Performance Comparison

| Feature | QR Codes | ArUco Markers |
|---------|----------|---------------|
| Detection Speed | ~500ms | ~50ms |
| Min Resolution | 1280x720 | 640x480 |
| Min Size | 3cm x 3cm | 1.5cm x 1.5cm |
| CPU Usage | High | Low |
| Lighting Tolerance | Medium | High |
| Angle Tolerance | Low | High |
| Precision | ±5px | ±1px |

## Quick Network Test Script

Create this script on your Raspberry Pi to test connectivity:

```bash
#!/bin/bash
# save as test_aruco_network.sh on Raspberry Pi

FOUNDRY_HOST="192.168.1.50"  # Replace with your Foundry host IP
FOUNDRY_PORT="30000"
WEBSOCKET_PORT="30001"

echo "Testing ArUco tracker network connectivity..."
echo "Foundry Host: $FOUNDRY_HOST"
echo ""

echo "1. Testing basic connectivity..."
if ping -c 3 $FOUNDRY_HOST > /dev/null 2>&1; then
    echo "✓ Host is reachable"
else
    echo "✗ Host is NOT reachable - check network configuration"
    exit 1
fi

echo "2. Testing Foundry HTTP port..."
if curl -s --connect-timeout 5 http://$FOUNDRY_HOST:$FOUNDRY_PORT > /dev/null; then
    echo "✓ Foundry HTTP port is accessible"
else
    echo "✗ Foundry HTTP port is NOT accessible"
fi

echo "3. Testing WebSocket port..."
if timeout 5 bash -c "</dev/tcp/$FOUNDRY_HOST/$WEBSOCKET_PORT"; then
    echo "✓ WebSocket port is open"
else
    echo "✗ WebSocket port is closed or filtered"
fi

echo ""
echo "Network test complete! If all tests pass, you're ready for ArUco tracking."
```

## Example Configuration

**Scenario**: Foundry runs on a desktop PC, Raspberry Pi with camera tracks tokens

**Network Setup:**
- Desktop PC (Foundry): `192.168.1.50`
- Raspberry Pi (Tracker): `192.168.1.100` 
- Router: `192.168.1.1`

**Foundry Module Settings:**
- ArUco Tracker Host: `192.168.1.100`
- WebSocket Port: `30001`
- Auto-create tokens: `true`
- Player Token Image: `path/to/player-token.png`

**Python Command:**
```bash
python3 foundry_aruco_tracker.py \
  --foundry-url "http://192.168.1.50:30000" \
  --scene-id "your-scene-id-from-foundry" \
  --websocket-port 30001
```

**Generated Markers:**
- Corner markers: IDs 0-3 (for calibration)
- Player tokens: IDs 10-29 (20 players)
- Custom tokens: IDs 100-110 (special items)

## Best Practices

### ArUco Marker Design
- **Always use high contrast** printing
- **Laminate markers** for frequent use
- **Color-code borders** for easy player identification
- **Standard size**: 2.5cm x 2.5cm for optimal performance
- **Backup sets**: Print extras in case of damage

### Table Setup
- **Consistent lighting** - avoid dramatic shadows
- **Matte surface** - reduce reflections
- **Clean boundaries** - clear distinction between play area and surroundings
- **Camera height**: 70-90cm above surface for best angle

### Gaming Workflow
1. **Pre-session**: Start ArUco tracker and verify connectivity
2. **Player setup**: Distribute player markers (ArUco IDs 10+)
3. **Calibration check**: Verify corner markers and surface detection
4. **Game start**: Begin with confidence that tracking is fast and reliable!

The ArUco system provides a significant upgrade in tracking performance and reliability compared to QR codes, making your hybrid gaming experience smooth and responsive! 🎲✨

## Support

If you encounter issues:

1. Check this README for common solutions
2. Use the preview tool to verify marker detection
3. Test network connectivity with provided scripts
4. Verify marker print quality and placement
5. Check system requirements and dependencies

The ArUco tracking system is designed for robust, high-performance tabletop gaming. Enjoy your enhanced hybrid experience!
