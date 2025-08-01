# 🎲 Mock FoundryVTT Server

An advanced async Python server that simulates FoundryVTT functionality for testing ArUco tracking systems when you don't have access to a real FoundryVTT instance. Built with aiohttp for high performance and real-time WebSocket communication.

## 📋 Overview

This professional-grade mock server provides comprehensive FoundryVTT simulation including visual scene representation, token management, and real-time ArUco marker tracking. Designed specifically for development and testing of tabletop gaming systems on Raspberry Pi devices.

## ✨ Features

### 🌐 Interactive Visual Dashboard
- **Real-time scene canvas** showing token positions with visual markers
- **Color-coded token types** (Player: red, Item: orange, Custom: purple)
- **Hover tooltips** with detailed token information
- **Live activity log** with timestamped events
- **Auto-reconnecting WebSocket** with connection status indicator
- **Interactive controls** for clearing tokens and managing view

### 🔌 Professional REST API
- **Comprehensive token management** with full CRUD operations
- **Scene-based organization** with multi-scene support
- **ArUco marker integration** with automatic token creation
- **Statistics tracking** with performance metrics
- **Proper HTTP status codes** and error handling
- **Token history tracking** for debugging and analysis

### ⚡ Advanced WebSocket System
- **Dual-port architecture** (HTTP: 30000, WebSocket: 30001)
- **Real-time position updates** with sub-second latency
- **Automatic token creation** from ArUco marker detection
- **Confidence-based filtering** for marker accuracy
- **Multi-client synchronization** across all connected devices
- **Handshake protocol** for ArUco tracker registration

### 🎯 Professional FoundryVTT Simulation
- **Authentic API structure** matching FoundryVTT patterns
- **Scene coordinate system** (4000x3000 default canvas size)
- **Token flagging system** for ArUco ID association
- **Marker type classification** (player, item, custom tokens)
- **Automatic naming conventions** based on marker types
- **Performance optimization** for Raspberry Pi deployment

## 🚀 Quick Start

### Prerequisites
- Python 3.7 or higher
- Raspberry Pi OS (or any Linux distribution)
- Network connectivity

### Installation

#### Option 1: Automated Setup (Recommended)

**Linux/Mac/Raspberry Pi:**
```bash
# Make setup script executable and run
chmod +x setup.sh
./setup.sh

# Follow the on-screen instructions
```

**Windows:**
```batch
# Double-click setup.bat or run from command prompt
setup.bat

# Follow the on-screen instructions
```

The setup scripts will:
- ✅ Check Python 3.7+ installation
- ✅ Create virtual environment automatically  
- ✅ Install all dependencies
- ✅ Provide clear next-step instructions
- ✅ Handle errors gracefully with helpful messages

#### Option 2: Manual Setup

1. **Clone or download the files:**
   ```bash
   # Create project directory
   mkdir mock-foundry-server
   cd mock-foundry-server
   
   # Copy mock_foundry_server.py, requirements.txt, and setup scripts here
   ```

2. **Set up virtual environment (RECOMMENDED):**
   ```bash
   # Create virtual environment
   python3 -m venv foundry-server-env
   
   # Activate virtual environment
   source foundry-server-env/bin/activate  # Linux/Mac
   # OR on Windows:
   # foundry-server-env\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Alternative: Direct installation (not recommended):**
   ```bash
   pip3 install aiohttp websockets
   ```

4. **Run the server (with virtual environment active):**
   ```bash
   # Basic usage (default ports 30000/30001)
   python3 mock_foundry_server.py
   
   # Custom ports
   python3 mock_foundry_server.py --port 8000 --ws-port 8001
   
   # Verbose logging for debugging
   python3 mock_foundry_server.py --verbose
   
   # Full options
   python3 mock_foundry_server.py --port 30000 --ws-port 30001 --verbose
   ```

5. **Access the dashboard:**
   - Web Interface: `http://localhost:30000` (local)
   - Or: `http://your-pi-ip:30000` (network access)
   - WebSocket: `ws://your-pi-ip:30001`

6. **Complete example session:**
   ```bash
   # Setup (one time)
   mkdir mock-foundry-server && cd mock-foundry-server
   # Copy files: mock_foundry_server.py, requirements.txt, setup.sh/setup.bat
   python3 -m venv foundry-server-env
   source foundry-server-env/bin/activate
   pip install -r requirements.txt
   
   # Development/testing (multiple runs)
   python3 mock_foundry_server.py --verbose
   python3 mock_foundry_server.py --port 8000 --ws-port 8001
   # ... test, debug, modify, repeat ...
   
   # Cleanup (when completely done)
   deactivate
   ```

### Command Line Options

```bash
# Setup Scripts
./setup.sh [OPTIONS]        # Linux/Mac/Pi automated setup
setup.bat                   # Windows automated setup

# Setup Script Options (Linux/Mac)
  -h, --help     Show help message
  -c, --clean    Remove existing virtual environment before setup

# Server Options  
python3 mock_foundry_server.py [OPTIONS]

Options:
  --port PORT       HTTP server port (default: 30000)
  --ws-port PORT    WebSocket server port (default: 30001)  
  --verbose, -v     Enable verbose logging
  --help, -h        Show help message
```

## 📖 Usage Guide

### Web Interface

The advanced dashboard provides:
- **Scene Canvas**: Visual representation of tokens with real-time positioning
- **Token Visualization**: Color-coded markers (🔴 Player, 🟠 Item, 🟣 Custom)
- **Interactive Tooltips**: Hover over tokens for detailed information
- **Live Statistics**: Server uptime, token count, connection status
- **Activity Log**: Real-time event logging with timestamps
- **Control Panel**: Clear tokens, reset view, toggle auto-refresh
- **Connection Monitor**: WebSocket status with auto-reconnection
- **Performance Metrics**: Update counts, API requests, response times

### API Endpoints

#### Scene & Token Management
```http
GET    /api/status                           # Server status and statistics
GET    /api/scenes                           # List all available scenes
GET    /api/scenes/{scene_id}/tokens         # Get tokens in specific scene
POST   /api/scenes/{scene_id}/tokens         # Create new token in scene
POST   /api/scenes/{scene_id}/clear          # Clear all tokens from scene
PATCH  /api/tokens/{token_id}                # Update existing token
```

#### WebSocket Protocol
```http
WebSocket: ws://server:30001                 # Real-time communication
```

## 🔧 Integration Examples

### Python ArUco Tracker Integration

```python
import asyncio
import aiohttp
import json

# Server configuration
HTTP_URL = "http://192.168.1.100:30000"
WS_URL = "ws://192.168.1.100:30001"
SCENE_ID = "test-scene-123"  # Default scene ID

class ArUcoFoundryClient:
    def __init__(self):
        self.session = None
        self.ws = None
    
    async def connect(self):
        """Initialize HTTP session and WebSocket connection"""
        self.session = aiohttp.ClientSession()
        self.ws = await self.session.ws_connect(WS_URL)
        
        # Send handshake
        await self.ws.send_str(json.dumps({
            "type": "handshake",
            "scene_id": SCENE_ID,
            "marker_system": "opencv_aruco"
        }))
        
        # Wait for handshake response
        response = await self.ws.receive()
        data = json.loads(response.data)
        print(f"Connected: {data.get('message')}")
    
    async def create_token(self, name, x, y, aruco_id=None, marker_type="custom"):
        """Create a new token in the scene"""
        data = {
            "name": name,
            "x": x,
            "y": y,
            "flags": {
                "aruco_id": aruco_id,
                "marker_type": marker_type
            }
        }
        
        async with self.session.post(f"{HTTP_URL}/api/scenes/{SCENE_ID}/tokens", json=data) as response:
            result = await response.json()
            print(f"Created token: {result.get('name')} at ({x}, {y})")
            return result
    
    async def send_aruco_update(self, aruco_id, x, y, confidence=1.0, marker_type="player"):
        """Send ArUco marker position update via WebSocket"""
        update_data = {
            "type": "token_update",
            "scene_id": SCENE_ID,
            "aruco_id": aruco_id,
            "x": x,
            "y": y,
            "confidence": confidence,
            "marker_type": marker_type
        }
        
        await self.ws.send_str(json.dumps(update_data))
        print(f"Sent ArUco update: ID {aruco_id} -> ({x}, {y}) confidence: {confidence}")
    
    async def listen_for_updates(self):
        """Listen for server updates (token changes, etc.)"""
        async for msg in self.ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = json.loads(msg.data)
                if data.get('type') == 'token_position_update':
                    token = data.get('token', {})
                    print(f"Server update: {token.get('name')} moved to ({token.get('x')}, {token.get('y')})")
    
    async def close(self):
        """Clean up connections"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()

# Example usage
async def main():
    client = ArUcoFoundryClient()
    
    try:
        await client.connect()
        
        # Create a test token
        await client.create_token("Test Player", 200, 300, aruco_id=15, marker_type="player")
        
        # Simulate ArUco detection updates
        for i in range(10):
            x = 200 + i * 10
            y = 300 + i * 5
            await client.send_aruco_update(15, x, y, confidence=0.95, marker_type="player")
            await asyncio.sleep(1)
    
    finally:
        await client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

### Real-time WebSocket Integration

```python
import asyncio
import websockets
import json

async def aruco_tracker_client():
    """Advanced ArUco tracker WebSocket client"""
    uri = "ws://192.168.1.100:30001"
    
    async with websockets.connect(uri) as websocket:
        # Send initial handshake
        handshake = {
            "type": "handshake",
            "scene_id": "test-scene-123",
            "marker_system": "opencv_aruco_4x4_50"
        }
        await websocket.send(json.dumps(handshake))
        
        # Handle incoming messages
        async def message_handler():
            async for message in websocket:
                data = json.loads(message)
                message_type = data.get('type')
                
                if message_type == 'handshake_ack':
                    print(f"✅ Handshake confirmed: {data.get('message')}")
                elif message_type == 'token_position_update':
                    token = data.get('token', {})
                    confidence = data.get('confidence', 0)
                    print(f"🎯 Token update: {token.get('name')} -> ({token.get('x')}, {token.get('y')}) [{confidence:.2f}]")
        
        # Start message handler
        handler_task = asyncio.create_task(message_handler())
        
        # Simulate ArUco detection loop
        marker_positions = {
            15: (250, 300),  # Player 1
            16: (400, 200),  # Player 2  
            30: (600, 450),  # Goblin enemy
            40: (150, 500)   # Treasure chest
        }
        
        try:
            for cycle in range(100):  # Continuous tracking
                for aruco_id, (base_x, base_y) in marker_positions.items():
                    # Simulate slight movement
                    x = base_x + (cycle % 20) - 10
                    y = base_y + (cycle % 15) - 7
                    
                    # Determine marker type
                    if 10 <= aruco_id <= 19:
                        marker_type = "player"
                    elif 30 <= aruco_id <= 39:
                        marker_type = "item"
                    elif 40 <= aruco_id <= 49:
                        marker_type = "item"
                    else:
                        marker_type = "custom"
                    
                    update = {
                        "type": "token_update",
                        "scene_id": "test-scene-123",
                        "aruco_id": aruco_id,
                        "x": x,
                        "y": y,
                        "confidence": 0.85 + (cycle % 10) * 0.01,  # Simulate confidence variation
                        "marker_type": marker_type
                    }
                    
                    await websocket.send(json.dumps(update))
                    await asyncio.sleep(0.1)  # 10 FPS update rate
                
                await asyncio.sleep(1)  # Pause between cycles
        
        except KeyboardInterrupt:
            print("🛑 Stopping ArUco tracker...")
        finally:
            handler_task.cancel()

# Run the client
asyncio.run(aruco_tracker_client())
```

## 🔍 API Reference

### Token Object Structure
```json
{
    "_id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Player_01",
    "x": 250,
    "y": 300,
    "img": "icons/svg/mystery-man.svg",
    "width": 1,
    "height": 1,
    "flags": {
        "aruco_id": 15,
        "marker_type": "player"
    },
    "created_at": 1627747200.0,
    "updated_at": 1627747260.5
}
```

### Scene Object Structure
```json
{
    "_id": "test-scene-123",
    "name": "ArUco Test Scene",
    "width": 4000,
    "height": 3000,
    "tokens": [/* array of token objects */],
    "created_at": 1627747200.0
}
```

### WebSocket Message Types

**Client → Server:**
- `handshake` - Initialize ArUco tracker connection
- `token_update` - Send ArUco marker position update

**Server → Client:**
- `welcome` - Initial connection confirmation
- `handshake_ack` - Handshake response
- `token_created` - New token added to scene
- `token_updated` - Token position/data changed
- `token_position_update` - Real-time position update
- `tokens_cleared` - All tokens removed from scene

### ArUco Marker Types & Auto-Naming

The server automatically creates appropriate token names based on ArUco marker IDs:

**Player Tokens (IDs 10-19):**
- ID 10 → "Player_01"
- ID 11 → "Player_02" 
- ID 15 → "Player_06"

**Enemy/NPC Tokens (IDs 30-39):**
- ID 30 → "Goblin"
- ID 31 → "Orc"
- ID 32 → "Skeleton"
- ID 33 → "Dragon"

**Item Tokens (IDs 40-49):**
- ID 40 → "Treasure_Chest"
- ID 41 → "Magic_Item"
- ID 42 → "Gold_Pile"
- ID 43 → "Potion"

**Special Tokens (IDs 50-61):**
- ID 50 → "NPC_Merchant"
- ID 55 → "Door"
- ID 60 → "Vehicle"

**Custom Tokens (Other IDs):**
- Any other ID → "Custom_{id}"

## 🛠️ Configuration

### Default Settings
- **HTTP Port**: `30000` (matches common FoundryVTT setups)
- **WebSocket Port**: `30001` (separate for better performance)
- **Host**: `0.0.0.0` (accepts connections from any IP)
- **Scene Size**: `4000x3000` pixels (standard tabletop dimensions)
- **Auto-reconnect**: `True` (WebSocket clients reconnect automatically)
- **Logging**: `INFO` level (use `--verbose` for DEBUG)

### Customization Options
- **Scene Dimensions**: Modify `MockScene` class constructor
- **Token Naming**: Edit the naming logic in `handle_websocket_message()`
- **ArUco ID Mapping**: Customize marker type classification
- **History Tracking**: Adjust `max_history` limit
- **Update Thresholds**: Configure position change sensitivity
- **Performance**: Tune async/await delays for your hardware

## 🐛 Troubleshooting

### Common Issues

**Ports Already in Use:**
```bash
# Check what's using ports 30000/30001
sudo netstat -tulpn | grep :30000
sudo netstat -tulpn | grep :30001

# Kill processes or use different ports
python3 mock_foundry_server.py --port 8000 --ws-port 8001
```

**Module Import Errors:**
```bash
# Install required async HTTP libraries
pip3 install aiohttp websockets

# For Raspberry Pi, you might need:
sudo apt update
sudo apt install python3-aiohttp python3-websockets
```

**WebSocket Connection Issues:**
```bash
# Test WebSocket connectivity
python3 -c "import asyncio, websockets
async def test(): 
    async with websockets.connect('ws://localhost:30001') as ws:
        print('WebSocket OK')
asyncio.run(test())"
```

**Performance Issues on Raspberry Pi:**
```bash
# Run with optimized settings
python3 mock_foundry_server.py --port 30000 --ws-port 30001

# Monitor system resources
htop
# Look for high CPU/memory usage
```

**Network Access Problems:**
```bash
# Check firewall for both ports
sudo ufw allow 30000
sudo ufw allow 30001

# Verify server is binding to all interfaces
netstat -tlnp | grep python3
```

**Async/Await Errors:**
- Ensure Python 3.7+ is installed (`python3 --version`)
- Update pip: `pip3 install --upgrade pip`
- Check for conflicting event loops in your code

### Debug Mode
Enable verbose logging for detailed troubleshooting:
```bash
python3 mock_foundry_server.py --verbose
```

This provides:
- Detailed WebSocket message logging
- HTTP request/response details
- Token creation/update traces
- Connection status monitoring
- Performance timing information

## 📁 File Structure

```
mock-foundry-server/
├── mock_foundry_server.py  # Main server script
├── requirements.txt        # Python dependencies
└── README.md              # This documentation
```

## 🤖 System Requirements

**Minimum:**
- Raspberry Pi 3B+ or better
- 512MB RAM available
- Python 3.7+
- 100MB disk space

**Recommended:**
- Raspberry Pi 4
- 1GB RAM available
- Python 3.9+
- Ethernet connection for stability

## 🔒 Security Notes

**Development Use Only:** This server is designed for testing and development. For production use:

- Add authentication/authorization
- Implement rate limiting
- Use HTTPS/WSS connections
- Validate all input data
- Run behind a reverse proxy

**Network Security:**
- The server accepts connections from any IP by default
- Consider firewall rules for network access
- Monitor server logs for unusual activity

## 📄 License

This project is provided as-is for educational and testing purposes. Use responsibly and ensure compliance with FoundryVTT's terms of service when integrating with actual FoundryVTT instances.

## 🤝 Contributing

Feel free to extend the server with additional features:
- More FoundryVTT API endpoints
- Database persistence
- User authentication
- Advanced scene management
- Combat tracking simulation

## 📞 Support

For issues related to:
- **ArUco tracking**: Check OpenCV and camera setup
- **Network connectivity**: Verify firewall and IP settings  
- **FoundryVTT integration**: Consult FoundryVTT API documentation
- **Python errors**: Check Python version and dependencies

---

**Happy Testing!** 🎲✨