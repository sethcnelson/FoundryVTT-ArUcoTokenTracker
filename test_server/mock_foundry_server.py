#!/usr/bin/env python3
"""
Mock Foundry VTT Server for ArUco Tracker Testing
=================================================

A lightweight mock server that simulates Foundry VTT's API and WebSocket
interface for testing the ArUco token tracker without a real Foundry server.

Features:
- HTTP API endpoints for token management
- WebSocket server for real-time communication
- Simple web interface to visualize tokens
- Scene and token management
- Logging of all tracker interactions

Usage:
python3 mock_foundry_server.py [--port 30000] [--ws-port 30001]

Access:
- Web Interface: http://localhost:30000
- API: http://localhost:30000/api/*
- WebSocket: ws://localhost:30001
"""

import asyncio
import json
import logging
import time
import uuid
import socket
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp
import websockets
from aiohttp import web, web_ws
from aiohttp.web import Response, WebSocketResponse
import argparse


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MockToken:
    """Represents a token in the mock Foundry server."""
    
    def __init__(self, token_id: str, name: str, x: int = 100, y: int = 100, 
                 img: str = "icons/svg/mystery-man.svg", width: int = 1, height: int = 1,
                 flags: Optional[Dict] = None):
        self.id = token_id
        self.name = name
        self.x = x
        self.y = y
        self.img = img
        self.width = width
        self.height = height
        self.flags = flags or {}
        self.created_at = time.time()
        self.updated_at = time.time()
    
    def to_dict(self) -> Dict:
        """Convert token to dictionary for API responses."""
        return {
            "_id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "img": self.img,
            "width": self.width,
            "height": self.height,
            "flags": self.flags,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    def update(self, data: Dict):
        """Update token with new data."""
        if "x" in data:
            self.x = data["x"]
        if "y" in data:
            self.y = data["y"]
        if "name" in data:
            self.name = data["name"]
        if "img" in data:
            self.img = data["img"]
        if "flags" in data:
            self.flags.update(data["flags"])
        self.updated_at = time.time()


class MockScene:
    """Represents a scene in the mock Foundry server."""
    
    def __init__(self, scene_id: str, name: str = "Test Scene", width: int = 4000, height: int = 3000):
        self.id = scene_id
        self.name = name
        self.width = width
        self.height = height
        self.tokens: Dict[str, MockToken] = {}
        self.created_at = time.time()
    
    def to_dict(self) -> Dict:
        """Convert scene to dictionary for API responses."""
        return {
            "_id": self.id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tokens": [token.to_dict() for token in self.tokens.values()],
            "created_at": self.created_at
        }


class MockFoundryServer:
    """Mock Foundry VTT server for testing ArUco tracker."""
    
    def __init__(self, ip_addr, http_port: int = 30000, ws_port: int = 30001):
        self.http_port = http_port
        self.ws_port = ws_port
        self.ip_addr = ip_addr
        
        # Create default scene
        self.default_scene_id = "test-scene-123"
        self.scenes: Dict[str, MockScene] = {
            self.default_scene_id: MockScene(self.default_scene_id, "ArUco Test Scene")
        }
        
        # WebSocket connections
        self.websocket_connections: set = set()
        
        # Statistics
        self.stats = {
            "tokens_created": 0,
            "tokens_updated": 0,
            "websocket_messages": 0,
            "api_requests": 0,
            "start_time": time.time()
        }
        
        # Token update history (for visualization)
        self.token_history: List[Dict] = []
        self.max_history = 1000
    
    def add_to_history(self, action: str, token_id: str, data: Dict):
        """Add token update to history."""
        self.token_history.append({
            "timestamp": time.time(),
            "action": action,
            "token_id": token_id,
            "data": data
        })
        
        # Keep only recent history
        if len(self.token_history) > self.max_history:
            self.token_history = self.token_history[-self.max_history:]
    
    async def broadcast_websocket(self, message: Dict):
        """Broadcast message to all WebSocket connections."""
        if not self.websocket_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = set()
        
        for ws in self.websocket_connections:
            try:
                await ws.send_str(message_str)
            except Exception as e:
                logger.warning(f"Failed to send WebSocket message: {e}")
                disconnected.add(ws)
        
        # Remove disconnected connections
        self.websocket_connections -= disconnected
        self.stats["websocket_messages"] += len(self.websocket_connections)
    
    # HTTP API Handlers
    
    async def handle_status(self, request):
        """Handle GET /api/status - Server status endpoint."""
        self.stats["api_requests"] += 1
        
        uptime = time.time() - self.stats["start_time"]
        status = {
            "status": "running",
            "server": "Mock Foundry VTT",
            "version": "1.0.0",
            "uptime": uptime,
            "scenes": len(self.scenes),
            "total_tokens": sum(len(scene.tokens) for scene in self.scenes.values()),
            "websocket_connections": len(self.websocket_connections),
            "stats": self.stats
        }
        
        return web.json_response(status)
    
    async def handle_get_scenes(self, request):
        """Handle GET /api/scenes - Get all scenes."""
        self.stats["api_requests"] += 1
        scenes = [scene.to_dict() for scene in self.scenes.values()]
        return web.json_response(scenes)
    
    async def handle_get_scene_tokens(self, request):
        """Handle GET /api/scenes/{scene_id}/tokens - Get tokens in scene."""
        self.stats["api_requests"] += 1
        scene_id = request.match_info['scene_id']
        
        if scene_id not in self.scenes:
            return web.json_response({"error": "Scene not found"}, status=404)
        
        scene = self.scenes[scene_id]
        tokens = [token.to_dict() for token in scene.tokens.values()]
        
        logger.info(f"API: Get tokens for scene {scene_id} - {len(tokens)} tokens")
        return web.json_response(tokens)
    
    async def handle_create_token(self, request):
        """Handle POST /api/scenes/{scene_id}/tokens - Create new token."""
        self.stats["api_requests"] += 1
        scene_id = request.match_info['scene_id']
        
        if scene_id not in self.scenes:
            return web.json_response({"error": "Scene not found"}, status=404)
        
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response({"error": f"Invalid JSON: {e}"}, status=400)
        
        # Create new token
        token_id = str(uuid.uuid4())
        token = MockToken(
            token_id=token_id,
            name=data.get("name", f"Token_{token_id[:8]}"),
            x=data.get("x", 100),
            y=data.get("y", 100),
            img=data.get("img", "icons/svg/mystery-man.svg"),
            width=data.get("width", 1),
            height=data.get("height", 1),
            flags=data.get("flags", {})
        )
        
        # Add to scene
        scene = self.scenes[scene_id]
        scene.tokens[token_id] = token
        
        self.stats["tokens_created"] += 1
        self.add_to_history("created", token_id, token.to_dict())
        
        logger.info(f"API: Created token {token.name} (ID: {token_id}) at ({token.x}, {token.y})")
        
        # Broadcast to WebSocket clients
        await self.broadcast_websocket({
            "type": "token_created",
            "scene_id": scene_id,
            "token": token.to_dict()
        })
        
        return web.json_response(token.to_dict(), status=201)
    
    async def handle_update_token(self, request):
        """Handle PATCH /api/tokens/{token_id} - Update existing token."""
        self.stats["api_requests"] += 1
        token_id = request.match_info['token_id']
        
        # Find token in any scene
        token = None
        scene_id = None
        for sid, scene in self.scenes.items():
            if token_id in scene.tokens:
                token = scene.tokens[token_id]
                scene_id = sid
                break
        
        if not token:
            return web.json_response({"error": "Token not found"}, status=404)
        
        try:
            data = await request.json()
        except Exception as e:
            return web.json_response({"error": f"Invalid JSON: {e}"}, status=400)
        
        # Update token
        old_pos = (token.x, token.y)
        token.update(data)
        new_pos = (token.x, token.y)
        
        self.stats["tokens_updated"] += 1
        self.add_to_history("updated", token_id, data)
        
        if old_pos != new_pos:
            logger.info(f"API: Updated token {token.name} position: {old_pos} -> {new_pos}")
        
        # Broadcast to WebSocket clients
        await self.broadcast_websocket({
            "type": "token_updated",
            "scene_id": scene_id,
            "token": token.to_dict()
        })
        
        return web.json_response(token.to_dict())
    
    async def handle_websocket(self, request):
        """Handle WebSocket connections."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websocket_connections.add(ws)
        client_info = f"{request.remote}:{request.transport.get_extra_info('peername')[1] if request.transport else 'unknown'}"
        logger.info(f"WebSocket: Client connected from {client_info}")
        
        try:
            # Send welcome message
            await ws.send_str(json.dumps({
                "type": "welcome",
                "message": "Connected to Mock Foundry Server",
                "scene_id": self.default_scene_id,
                "server_time": time.time()
            }))
            
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self.handle_websocket_message(ws, data)
                    except json.JSONDecodeError as e:
                        logger.warning(f"WebSocket: Invalid JSON from {client_info}: {e}")
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON"
                        }))
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.warning(f"WebSocket error from {client_info}: {ws.exception()}")
                    break
        
        except Exception as e:
            logger.warning(f"WebSocket connection error: {e}")
        finally:
            self.websocket_connections.discard(ws)
            logger.info(f"WebSocket: Client disconnected from {client_info}")
        
        return ws
    
    async def handle_websocket_message(self, ws, data: Dict):
        """Handle incoming WebSocket messages."""
        message_type = data.get("type", "unknown")
        logger.info(f"WebSocket: Received {message_type} message")
        
        if message_type == "handshake":
            # ArUco tracker handshake
            await ws.send_str(json.dumps({
                "type": "handshake_ack",
                "message": "Mock Foundry Server ready",
                "scene_id": data.get("scene_id", self.default_scene_id),
                "marker_system": data.get("marker_system", "unknown")
            }))
        
        elif message_type == "token_update":
            # Handle token update from ArUco tracker
            scene_id = data.get("scene_id", self.default_scene_id)
            aruco_id = data.get("aruco_id")
            token_id = data.get("token_id")
            x = data.get("x", 0)
            y = data.get("y", 0)
            confidence = data.get("confidence", 1.0)
            marker_type = data.get("marker_type", "unknown")
            
            logger.info(f"WebSocket: ArUco update - ID:{aruco_id} -> ({x}, {y}) confidence:{confidence:.2f}")
            
            # Find or create token
            if scene_id in self.scenes:
                scene = self.scenes[scene_id]
                
                # Try to find existing token
                token = None
                if token_id and token_id in scene.tokens:
                    token = scene.tokens[token_id]
                else:
                    # Look for token by ArUco ID in flags
                    for t in scene.tokens.values():
                        if t.flags.get("aruco_id") == aruco_id:
                            token = t
                            break
                
                if not token:
                    # Create new token
                    new_token_id = str(uuid.uuid4())
                    
                    # Generate name based on marker type
                    if marker_type == 'player':
                        player_num = aruco_id - 10 + 1
                        name = f"Player_{player_num:02d}"
                    elif marker_type == 'item':
                        item_names = {
                            30: "Goblin", 31: "Orc", 32: "Skeleton", 33: "Dragon", 34: "Troll",
                            35: "Wizard_Enemy", 36: "Beast", 37: "Demon", 40: "Treasure_Chest",
                            41: "Magic_Item", 42: "Gold_Pile", 43: "Potion", 44: "Weapon",
                            45: "Armor", 46: "Scroll", 47: "Key", 50: "NPC_Merchant",
                            51: "NPC_Guard", 52: "NPC_Noble", 53: "NPC_Innkeeper", 54: "NPC_Priest",
                            55: "Door", 56: "Trap", 57: "Fire_Hazard", 58: "Altar",
                            59: "Portal", 60: "Vehicle", 61: "Objective"
                        }
                        name = item_names.get(aruco_id, f"Item_{aruco_id}")
                    else:
                        name = f"Custom_{aruco_id}"
                    
                    token = MockToken(
                        token_id=new_token_id,
                        name=name,
                        x=x, y=y,
                        flags={"aruco_id": aruco_id, "marker_type": marker_type}
                    )
                    scene.tokens[new_token_id] = token
                    self.stats["tokens_created"] += 1
                    
                    logger.info(f"WebSocket: Created new token {name} for ArUco {aruco_id}")
                else:
                    # Update existing token position
                    old_pos = (token.x, token.y)
                    token.update({"x": x, "y": y})
                    self.stats["tokens_updated"] += 1
                    
                    if abs(old_pos[0] - x) > 5 or abs(old_pos[1] - y) > 5:  # Only log significant moves
                        logger.info(f"WebSocket: Moved {token.name}: {old_pos} -> ({x}, {y})")
                
                # Broadcast update to other clients
                await self.broadcast_websocket({
                    "type": "token_position_update",
                    "scene_id": scene_id,
                    "token": token.to_dict(),
                    "aruco_id": aruco_id,
                    "confidence": confidence
                })
        
        else:
            logger.warning(f"WebSocket: Unknown message type: {message_type}")
    
    # Web Interface Handlers
    
    async def handle_index(self, request):
        """Handle GET / - Main web interface."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Mock Foundry VTT Server</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .header {{ background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 20px; }}
        .stat-card {{ background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .stat-value {{ font-size: 2em; font-weight: bold; color: #3498db; }}
        .scene-container {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .scene-canvas {{ border: 2px solid #34495e; background: #ecf0f1; position: relative; margin: 20px 0; }}
        .token {{ position: absolute; width: 20px; height: 20px; border-radius: 50%; border: 2px solid #2c3e50; display: flex; align-items: center; justify-content: center; font-size: 10px; font-weight: bold; color: white; text-shadow: 1px 1px 1px rgba(0,0,0,0.5); cursor: pointer; }}
        .token.player {{ background: #e74c3c; }}
        .token.item {{ background: #f39c12; }}
        .token.custom {{ background: #9b59b6; }}
        .token.unknown {{ background: #95a5a6; }}
        .log {{ background: #2c3e50; color: #ecf0f1; padding: 15px; border-radius: 8px; font-family: monospace; font-size: 12px; max-height: 300px; overflow-y: auto; }}
        .log-entry {{ margin: 2px 0; }}
        .controls {{ margin: 20px 0; }}
        .btn {{ background: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin-right: 10px; }}
        .btn:hover {{ background: #2980b9; }}
        .connection-status {{ padding: 10px; border-radius: 4px; margin: 10px 0; }}
        .connected {{ background: #d5f4e6; color: #27ae60; }}
        .disconnected {{ background: #fadbd8; color: #e74c3c; }}
        #tokenInfo {{ position: absolute; background: rgba(0,0,0,0.8); color: white; padding: 8px; border-radius: 4px; pointer-events: none; display: none; z-index: 1000; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎲 Mock Foundry VTT Server</h1>
            <p>Testing server for ArUco Token Tracker - Listening on port {self.http_port}</p>
            <div id="connectionStatus" class="connection-status disconnected">WebSocket: Disconnected</div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="tokenCount">{sum(len(scene.tokens) for scene in self.scenes.values())}</div>
                <div>Active Tokens</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="connectionCount">{len(self.websocket_connections)}</div>
                <div>WebSocket Connections</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="updateCount">{self.stats['tokens_updated']}</div>
                <div>Token Updates</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="uptime">{int(time.time() - self.stats['start_time'])}s</div>
                <div>Server Uptime</div>
            </div>
        </div>
        
        <div class="scene-container">
            <h2>🗺️ Scene: ArUco Test Scene</h2>
            <div class="controls">
                <button class="btn" onclick="clearTokens()">Clear All Tokens</button>
                <button class="btn" onclick="resetView()">Reset View</button>
                <button class="btn" onclick="toggleAutoRefresh()">Toggle Auto-Refresh</button>
            </div>
            <div id="sceneCanvas" class="scene-canvas" style="width: 800px; height: 600px;"></div>
            <div id="tokenInfo"></div>
        </div>
        
        <div class="scene-container">
            <h2>📋 Activity Log</h2>
            <div id="activityLog" class="log"></div>
        </div>
        
        <div class="scene-container">
            <h2>🔧 API Endpoints</h2>
            <ul>
                <li><strong>GET</strong> /api/status - Server status</li>
                <li><strong>GET</strong> /api/scenes - List scenes</li>
                <li><strong>GET</strong> /api/scenes/{scene_id}/tokens - Get scene tokens</li>
                <li><strong>POST</strong> /api/scenes/{scene_id}/tokens - Create token</li>
                <li><strong>PATCH</strong> /api/tokens/{token_id} - Update token</li>
                <li><strong>WebSocket</strong> ws://{self.ip_addr}:{self.ws_port} - Real-time updates</li>
            </ul>
        </div>
    </div>
    
    <script>
        let ws = null;
        let autoRefresh = true;
        let tokens = new Map();
        
        function connectWebSocket() {{
            try {{
                ws = new WebSocket('ws://{self.ip_addr}:{self.ws_port}');
                
                ws.onopen = function() {{
                    document.getElementById('connectionStatus').textContent = 'WebSocket: Connected';
                    document.getElementById('connectionStatus').className = 'connection-status connected';
                    addLogEntry('🟢 WebSocket connected');
                }};
                
                ws.onmessage = function(event) {{
                    const data = JSON.parse(event.data);
                    handleWebSocketMessage(data);
                }};
                
                ws.onclose = function() {{
                    document.getElementById('connectionStatus').textContent = 'WebSocket: Disconnected';
                    document.getElementById('connectionStatus').className = 'connection-status disconnected';
                    addLogEntry('🔴 WebSocket disconnected');
                    
                    // Auto-reconnect
                    setTimeout(connectWebSocket, 3000);
                }};
                
                ws.onerror = function(error) {{
                    addLogEntry('❌ WebSocket error: ' + error);
                }};
            }} catch (error) {{
                addLogEntry('❌ Failed to connect WebSocket: ' + error);
                setTimeout(connectWebSocket, 3000);
            }}
        }}
        
        function handleWebSocketMessage(data) {{
            if (data.type === 'token_created' || data.type === 'token_updated' || data.type === 'token_position_update') {{
                updateToken(data.token);
                addLogEntry(`🎯 Token ${{data.token.name}} updated: (${{data.token.x}}, ${{data.token.y}})`);
                updateStats();
            }} else if (data.type === 'welcome') {{
                addLogEntry('👋 ' + data.message);
            }}
        }}
        
        function updateToken(tokenData) {{
            tokens.set(tokenData._id, tokenData);
            renderTokens();
        }}
        
        function renderTokens() {{
            const canvas = document.getElementById('sceneCanvas');
            const canvasRect = canvas.getBoundingClientRect();
            
            // Clear existing tokens
            canvas.querySelectorAll('.token').forEach(el => el.remove());
            
            // Render each token
            tokens.forEach(token => {{
                const tokenEl = document.createElement('div');
                tokenEl.className = 'token ' + (token.flags.marker_type || 'unknown');
                tokenEl.style.left = (token.x / 4000 * 800 - 10) + 'px';
                tokenEl.style.top = (token.y / 3000 * 600 - 10) + 'px';
                tokenEl.textContent = getTokenSymbol(token);
                tokenEl.title = `${{token.name}} (${{token.x}}, ${{token.y}})`;
                
                // Add hover info
                tokenEl.addEventListener('mouseenter', (e) => showTokenInfo(e, token));
                tokenEl.addEventListener('mouseleave', hideTokenInfo);
                
                canvas.appendChild(tokenEl);
            }});
        }}
        
        function getTokenSymbol(token) {{
            const markerType = token.flags.marker_type;
            if (markerType === 'player') return 'P';
            if (markerType === 'item') return 'I';
            if (markerType === 'custom') return 'C';
            return '?';
        }}
        
        function showTokenInfo(event, token) {{
            const info = document.getElementById('tokenInfo');
            info.style.display = 'block';
            info.style.left = (event.pageX + 10) + 'px';
            info.style.top = (event.pageY - 30) + 'px';
            info.innerHTML = `
                <strong>${{token.name}}</strong><br>
                Position: (${{token.x}}, ${{token.y}})<br>
                ArUco ID: ${{token.flags.aruco_id || 'N/A'}}<br>
                Type: ${{token.flags.marker_type || 'Unknown'}}
            `;
        }}
        
        function hideTokenInfo() {{
            document.getElementById('tokenInfo').style.display = 'none';
        }}
        
        function addLogEntry(message) {{
            const log = document.getElementById('activityLog');
            const entry = document.createElement('div');
            entry.className = 'log-entry';
            entry.textContent = new Date().toLocaleTimeString() + ' - ' + message;
            log.appendChild(entry);
            log.scrollTop = log.scrollHeight;
        }}
        
        function updateStats() {{
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('tokenCount').textContent = data.total_tokens;
                    document.getElementById('connectionCount').textContent = data.websocket_connections;
                    document.getElementById('updateCount').textContent = data.stats.tokens_updated;
                    document.getElementById('uptime').textContent = Math.floor(data.uptime) + 's';
                }});
        }}
        
        function clearTokens() {{
            if (confirm('Clear all tokens?')) {{
                fetch('/api/scenes/{self.default_scene_id}/clear', {{method: 'POST'}})
                    .then(() => {{
                        tokens.clear();
                        renderTokens();
                        addLogEntry('🗑️ All tokens cleared');
                    }});
            }}
        }}
        
        function resetView() {{
            renderTokens();
            addLogEntry('🔄 View reset');
        }}
        
        function toggleAutoRefresh() {{
            autoRefresh = !autoRefresh;
            addLogEntry('🔄 Auto-refresh ' + (autoRefresh ? 'enabled' : 'disabled'));
        }}
        
        // Initialize
        connectWebSocket();
        updateStats();
        
        // Auto-refresh stats
        setInterval(() => {{
            if (autoRefresh) {{
                updateStats();
            }}
        }}, 2000);
        
        // Load initial tokens
        fetch('/api/scenes/{self.default_scene_id}/tokens')
            .then(response => response.json())
            .then(tokenList => {{
                tokenList.forEach(token => {{
                    tokens.set(token._id, token);
                }});
                renderTokens();
            }});
    </script>
</body>
</html>
        """
        return web.Response(text=html, content_type='text/html')
    
    async def handle_clear_tokens(self, request):
        """Handle POST /api/scenes/{scene_id}/clear - Clear all tokens."""
        scene_id = request.match_info['scene_id']
        
        if scene_id not in self.scenes:
            return web.json_response({"error": "Scene not found"}, status=404)
        
        scene = self.scenes[scene_id]
        token_count = len(scene.tokens)
        scene.tokens.clear()
        
        logger.info(f"API: Cleared {token_count} tokens from scene {scene_id}")
        
        # Broadcast to WebSocket clients
        await self.broadcast_websocket({
            "type": "tokens_cleared",
            "scene_id": scene_id
        })
        
        return web.json_response({"message": f"Cleared {token_count} tokens"})
    
    def create_app(self):
        """Create the aiohttp web application."""
        app = web.Application()
        
        # API routes
        app.router.add_get('/api/status', self.handle_status)
        app.router.add_get('/api/scenes', self.handle_get_scenes)
        app.router.add_get('/api/scenes/{scene_id}/tokens', self.handle_get_scene_tokens)
        app.router.add_post('/api/scenes/{scene_id}/tokens', self.handle_create_token)
        app.router.add_post('/api/scenes/{scene_id}/clear', self.handle_clear_tokens)
        app.router.add_patch('/api/tokens/{token_id}', self.handle_update_token)
        
        # Web interface
        app.router.add_get('/', self.handle_index)
        
        return app
    
    async def start_websocket_server(self):
        """Start the WebSocket server."""
        async def websocket_handler(websocket, path):
            await websocket.send(json.dumps({
                "type": "welcome",
                "message": "Connected to Mock Foundry WebSocket Server",
                "scene_id": self.default_scene_id
            }))
            
            self.websocket_connections.add(websocket)
            logger.info(f"WebSocket: Client connected from {websocket.remote_address}")
            
            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        # Handle the message (similar to aiohttp handler)
                        # For simplicity, we'll just echo back
                        await websocket.send(json.dumps({
                            "type": "echo",
                            "data": data
                        }))
                    except json.JSONDecodeError:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Invalid JSON"
                        }))
            except Exception as e:
                logger.warning(f"WebSocket error: {e}")
            finally:
                self.websocket_connections.discard(websocket)
                logger.info(f"WebSocket: Client disconnected")
        
        # Start WebSocket server
        start_server = websockets.serve(websocket_handler, {self.ip_addr}, self.ws_port)
        await start_server
        logger.info(f"WebSocket server started on port {self.ws_port}")
    
    async def run(self):
        """Run the mock Foundry server."""
        # Create HTTP app
        app = self.create_app()
        
        # Start WebSocket server
        asyncio.create_task(self.start_websocket_server())
        
        # Start HTTP server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, {self.ip_addr}, self.http_port)
        await site.start()
        
        logger.info(f"Mock Foundry VTT Server started!")
        logger.info(f"HTTP Server: http://{self.ip_addr}:{self.http_port}")
        logger.info(f"WebSocket Server: ws://{self.ip_addr}:{self.ws_port}")
        logger.info(f"Default Scene ID: {self.default_scene_id}")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await runner.cleanup()

import socket

def ip_addr(hostIP=None):
    if hostIP is None or hostIP == 'auto':
        hostIP = 'ip'

    if hostIP == 'dns':
        hostIP = socket.getfqdn()
    elif hostIP == 'ip':
        from socket import gaierror
        try:
            hostIP = socket.gethostbyname(socket.getfqdn())
        except gaierror:
            # logger.warn('gethostbyname(socket.getfqdn()) failed... trying on hostname()')
            hostIP = socket.gethostbyname(socket.gethostname())
        if hostIP.startswith("127."):
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # doesn't have to be reachable
            s.connect(('10.255.255.255', 1))
            hostIP = s.getsockname()[0]
    return hostIP


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Mock Foundry VTT Server for ArUco Testing")
    parser.add_argument("--ip_addr", type=str, default="", help="IP address for HTTP and WebSocket server (default: current IP address)")
    parser.add_argument("--port", type=int, default=30000, help="HTTP server port (default: 30000)")
    parser.add_argument("--ws-port", type=int, default=30001, help="WebSocket server port (default: 30001)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not args.ip_addr:
        args.ip_addr = get_local_ip_address()
    
    # Create and run server
    server = MockFoundryServer(ip_addr=args.ip_addr, http_port=args.port, ws_port=args.ws_port)
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
