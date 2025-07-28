// Foundry VTT ArUco Tracker Module
// Place this in: Data/modules/aruco-tracker/aruco-tracker.js

class ArucoTrackerModule {
    constructor() {
        this.websocket = null;
        this.isConnected = false;
        this.lastConnectionAttempt = null;
        this.config = {
            websocketPort: 30001,
            reconnectInterval: 5000,
            updateThrottle: 100
        };
        this.lastUpdate = {};
        this.tokenCache = new Map();
        this.markerSchema = {
            corner: [0, 1, 2, 3],
            player: [10, 25],    // 16 players (IDs 10-25)
            item: [30, 61],      // 32 standard items (IDs 30-61)
            custom: [62, 999]    // Custom markers (IDs 62+)
        };
    }

    async initialize() {
        console.log("ArUco Tracker | Initializing module");
        
        // Add module settings
        this.registerSettings();
        
        // Set up WebSocket connection
        this.connectWebSocket();
        
        // Set up file watcher as backup
        this.setupFileWatcher();
        
        // Add UI controls
        this.addControls();
    }

    registerSettings() {
        game.settings.register("aruco-tracker", "trackerHost", {
            name: "ArUco Tracker Host",
            hint: "IP address or hostname of the ArUco tracker (Raspberry Pi)",
            scope: "world",
            config: true,
            type: String,
            default: "localhost"
        });

        game.settings.register("aruco-tracker", "websocketPort", {
            name: "WebSocket Port",
            hint: "Port for ArUco tracker WebSocket connection",
            scope: "world",
            config: true,
            type: Number,
            default: 30001
        });

        game.settings.register("aruco-tracker", "autoCreateTokens", {
            name: "Auto-Create Tokens",
            hint: "Automatically create tokens for new ArUco markers",
            scope: "world",
            config: true,
            type: Boolean,
            default: true
        });

        game.settings.register("aruco-tracker", "tokenImagePath", {
            name: "Default Token Image",
            hint: "Default image for auto-created tokens",
            scope: "world",
            config: true,
            type: String,
            default: "icons/svg/mystery-man.svg"
        });

        game.settings.register("aruco-tracker", "playerTokenImage", {
            name: "Player Token Image",
            hint: "Specific image for player tokens (ArUco IDs 10-25)",
            scope: "world",
            config: true,
            type: String,
            default: "icons/svg/mystery-man.svg"
        });

        game.settings.register("aruco-tracker", "itemTokenImage", {
            name: "Item Token Image",
            hint: "Specific image for item tokens (ArUco IDs 30-61)",
            scope: "world",
            config: true,
            type: String,
            default: "icons/svg/item-bag.svg"
        });

        game.settings.register("aruco-tracker", "enableCORS", {
            name: "Enable CORS Headers",
            hint: "Add CORS headers for cross-origin requests from tracker",
            scope: "world",
            config: true,
            type: Boolean,
            default: true
        });
    }

    connectWebSocket() {
        const trackerHost = game.settings.get("aruco-tracker", "trackerHost");
        const port = game.settings.get("aruco-tracker", "websocketPort");
        const wsUrl = `ws://${trackerHost}:${port}`;
        
        console.log(`ArUco Tracker | Attempting connection to: ${wsUrl}`);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log("ArUco Tracker | WebSocket connected to remote tracker");
                this.isConnected = true;
                ui.notifications.info(`ArUco Tracker connected to ${trackerHost}`);
                
                // Send handshake with Foundry info
                this.websocket.send(JSON.stringify({
                    type: "foundry_ready",
                    scene_id: game.scenes.active?.id,
                    foundry_host: window.location.hostname,
                    foundry_port: window.location.port || 30000,
                    user_id: game.user.id,
                    marker_system: "aruco",
                    timestamp: Date.now()
                }));
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.websocket.onclose = (event) => {
                console.log(`ArUco Tracker | WebSocket disconnected (Code: ${event.code})`);
                this.isConnected = false;
                
                if (event.code !== 1000) { // Not a normal closure
                    ui.notifications.warn(`ArUco Tracker disconnected from ${trackerHost}`);
                }
                
                // Attempt reconnection for non-intentional disconnects
                if (event.code !== 1000 && event.code !== 1001) {
                    setTimeout(() => {
                        if (!this.isConnected) {
                            console.log("ArUco Tracker | Attempting reconnection...");
                            this.connectWebSocket();
                        }
                    }, this.config.reconnectInterval);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error("ArUco Tracker | WebSocket error:", error);
                ui.notifications.error(`Failed to connect to ArUco tracker at ${trackerHost}:${port}`);
            };
            
        } catch (error) {
            console.error("ArUco Tracker | Failed to create WebSocket connection:", error);
            ui.notifications.error(`Cannot connect to ArUco tracker: ${error.message}`);
        }
    }

    async handleWebSocketMessage(data) {
        switch (data.type) {
            case "token_update":
                await this.updateTokenPosition(data);
                break;
            case "handshake":
                console.log("ArUco Tracker | Received handshake from tracker");
                if (data.marker_system === "aruco") {
                    console.log("ArUco Tracker | Confirmed ArUco marker system");
                }
                break;
            default:
                console.log("ArUco Tracker | Unknown message type:", data.type);
        }
    }

    getMarkerType(arucoId) {
        if (this.markerSchema.corner.includes(arucoId)) {
            return 'corner';
        } else if (arucoId >= this.markerSchema.player[0] && arucoId <= this.markerSchema.player[1]) {
            return 'player';
        } else if (arucoId >= this.markerSchema.item[0] && arucoId <= this.markerSchema.item[1]) {
            return 'item';
        } else if (arucoId >= this.markerSchema.custom[0] && arucoId <= this.markerSchema.custom[1]) {
            return 'custom';
        }
        return 'unknown';
    }

    getItemName(arucoId) {
        const itemNames = {
            30: "Goblin", 31: "Orc", 32: "Skeleton", 33: "Dragon", 34: "Troll", 35: "Wizard_Enemy", 36: "Beast", 37: "Demon",
            40: "Treasure_Chest", 41: "Magic_Item", 42: "Gold_Pile", 43: "Potion", 44: "Weapon", 45: "Armor", 46: "Scroll", 47: "Key",
            50: "NPC_Merchant", 51: "NPC_Guard", 52: "NPC_Noble", 53: "NPC_Innkeeper", 54: "NPC_Priest",
            55: "Door", 56: "Trap", 57: "Fire_Hazard", 58: "Altar", 59: "Portal", 60: "Vehicle", 61: "Objective"
        };
        return itemNames[arucoId] || `Item_${arucoId}`;
    }

    generateTokenName(arucoId, markerType) {
        switch (markerType) {
            case 'player':
                const playerNum = arucoId - 10 + 1;
                return `Player_${playerNum.toString().padStart(2, '0')}`;
            case 'item':
                return this.getItemName(arucoId);
            case 'custom':
                return `Custom_${arucoId}`;
            case 'corner':
                return `Corner_${arucoId}`;
            default:
                return `ArUco_${arucoId}`;
        }
    }

    async updateTokenPosition(data) {
        const { aruco_id, token_id, x, y, confidence, scene_id, marker_type } = data;
        
        // Check if this is for the current scene
        if (scene_id && scene_id !== game.scenes.active?.id) {
            return;
        }
        
        // Skip corner markers - they're for calibration only
        if (this.getMarkerType(aruco_id) === 'corner') {
            return;
        }
        
        // Throttle updates
        const now = Date.now();
        const lastUpdate = this.lastUpdate[aruco_id] || 0;
        if (now - lastUpdate < this.config.updateThrottle) {
            return;
        }
        this.lastUpdate[aruco_id] = now;
        
        try {
            let token = null;
            
            // Find token by ID or ArUco mapping
            if (token_id) {
                token = game.scenes.active.tokens.get(token_id);
            }
            
            if (!token) {
                // Look for token by ArUco ID in flags
                token = game.scenes.active.tokens.find(t => 
                    t.getFlag("aruco-tracker", "aruco_id") === aruco_id
                );
            }
            
            if (!token) {
                // Create new token if auto-create is enabled
                if (game.settings.get("aruco-tracker", "autoCreateTokens")) {
                    token = await this.createTokenForArUco(aruco_id, x, y, marker_type);
                } else {
                    console.warn(`ArUco Tracker | No token found for ArUco ID: ${aruco_id}`);
                    return;
                }
            }
            
            if (token) {
                // Update token position
                await token.update({
                    x: x,
                    y: y
                });
                
                // Store in cache
                this.tokenCache.set(aruco_id, {
                    tokenId: token.id,
                    lastSeen: now,
                    confidence: confidence,
                    markerType: marker_type || this.getMarkerType(aruco_id)
                });
                
                console.log(`ArUco Tracker | Updated token ${token.name} (ArUco ${aruco_id}) to (${x}, ${y})`);
            }
            
        } catch (error) {
            console.error("ArUco Tracker | Error updating token:", error);
        }
    }

    async createTokenForArUco(aruco_id, x, y, marker_type) {
        const detectedMarkerType = marker_type || this.getMarkerType(aruco_id);
        const tokenName = this.generateTokenName(aruco_id, detectedMarkerType);
        
        // Choose appropriate token image based on marker type
        let tokenImage;
        switch (detectedMarkerType) {
            case 'player':
                tokenImage = game.settings.get("aruco-tracker", "playerTokenImage");
                break;
            case 'item':
                tokenImage = game.settings.get("aruco-tracker", "itemTokenImage");
                break;
            default:
                tokenImage = game.settings.get("aruco-tracker", "tokenImagePath");
                break;
        }
        
        const tokenData = {
            name: tokenName,
            img: tokenImage,
            x: x,
            y: y,
            width: 1,
            height: 1,
            flags: {
                "aruco-tracker": {
                    aruco_id: aruco_id,
                    marker_type: detectedMarkerType,
                    created_by_tracker: true,
                    created_at: Date.now()
                }
            }
        };
        
        try {
            const tokenDocument = await game.scenes.active.createEmbeddedDocuments("Token", [tokenData]);
            const token = tokenDocument[0];
            
            ui.notifications.info(`Created ${detectedMarkerType} token: ${tokenName} (ArUco ${aruco_id})`);
            console.log(`ArUco Tracker | Created token for ArUco ${aruco_id}:`, token);
            
            return token;
        } catch (error) {
            console.error("ArUco Tracker | Failed to create token:", error);
            return null;
        }
    }

    setupFileWatcher() {
        // File watcher as backup method
        // This would need to be implemented with a file system watcher
        // For now, we'll use a simple polling mechanism
        
        setInterval(async () => {
            try {
                // This would need to be adapted based on how Foundry can access files
                // You might need to serve the JSON file via HTTP instead
                const response = await fetch('/modules/aruco-tracker/token_data.json');
                if (response.ok) {
                    const data = await response.json();
                    if (data.marker_system === "aruco") {
                        await this.processFileData(data);
                    }
                }
            } catch (error) {
                // File not available, continue silently
            }
        }, 1000); // Check every second
    }

    async processFileData(data) {
        if (!data.tokens || !Array.isArray(data.tokens)) return;
        
        for (const tokenData of data.tokens) {
            await this.updateTokenPosition({
                type: "token_update",
                aruco_id: tokenData.aruco_id,
                token_id: tokenData.foundry_token_id,
                x: tokenData.x,
                y: tokenData.y,
                confidence: tokenData.confidence,
                marker_type: tokenData.marker_type,
                scene_id: data.scene_id
            });
        }
    }

    addControls() {
        // Add token controls to the scene controls
        Hooks.on("getSceneControlButtons", (controls) => {
            const tokenControls = controls.find(c => c.name === "token");
            if (tokenControls) {
                tokenControls.tools.push({
                    name: "aruco-tracker-status",
                    title: "ArUco Tracker Status",
                    icon: this.isConnected ? "fas fa-wifi" : "fas fa-exclamation-triangle",
                    onClick: () => this.showStatusDialog(),
                    button: true
                });
            }
        });
    }

    showStatusDialog() {
        const trackerHost = game.settings.get("aruco-tracker", "trackerHost");
        const port = game.settings.get("aruco-tracker", "websocketPort");
        
        const content = `
            <div>
                <h3>ArUco Tracker Status</h3>
                <p><strong>Tracker Host:</strong> ${trackerHost}:${port}</p>
                <p><strong>Connection:</strong> ${this.isConnected ? 'Connected ✓' : 'Disconnected ✗'}</p>
                <p><strong>Tracked Tokens:</strong> ${this.tokenCache.size}</p>
                <p><strong>Active Scene:</strong> ${game.scenes.active?.name || 'None'}</p>
                <p><strong>Foundry Host:</strong> ${window.location.hostname}:${window.location.port || 30000}</p>
                
                <h4>ArUco Marker Schema (Optimized):</h4>
                <ul style="font-size: 0.9em;">
                    <li><strong>Corner markers:</strong> IDs 0-3 (calibration only)</li>
                    <li><strong>Player tokens:</strong> IDs 10-25 (16 players max)</li>
                    <li><strong>Item tokens:</strong> IDs 30-61 (32 standard items)</li>
                    <li><strong>Custom tokens:</strong> IDs 62+ (user defined)</li>
                </ul>
                
                <h4>Optimization Benefits:</h4>
                <ul style="font-size: 0.9em;">
                    <li>✓ Smaller physical markers (15mm minimum)</li>
                    <li>✓ Faster detection performance</li>
                    <li>✓ Total standard IDs: 52 (vs 90+ previously)</li>
                    <li>✓ Better for tabletop gaming use cases</li>
                </ul>
                
                <h4>Network Diagnostics:</h4>
                <p><strong>WebSocket URL:</strong> ws://${trackerHost}:${port}</p>
                <p><strong>Last Connection Attempt:</strong> ${this.lastConnectionAttempt || 'Never'}</p>
                
                <h4>Tracked ArUco Markers:</h4>
                ${this.tokenCache.size > 0 ? `
                    <ul>
                        ${Array.from(this.tokenCache.entries()).map(([arucoId, data]) => {
                            const markerType = data.markerType || 'unknown';
                            const typeLabel = markerType.charAt(0).toUpperCase() + markerType.slice(1);
                            return `<li>ArUco ${arucoId} (${typeLabel}, Confidence: ${data.confidence?.toFixed(2) || 'N/A'}, Last seen: ${new Date(data.lastSeen).toLocaleTimeString()})</li>`;
                        }).join('')}
                    </ul>
                ` : '<p><em>No ArUco markers currently tracked</em></p>'}
                
                <div style="margin-top: 15px;">
                    <button type="button" onclick="game.modules.get('aruco-tracker').api.reconnect()">
                        Reconnect to Tracker
                    </button>
                    <button type="button" onclick="game.modules.get('aruco-tracker').api.testConnection()">
                        Test Connection
                    </button>
                </div>
                
                <h4>Troubleshooting:</h4>
                <ul style="font-size: 0.9em;">
                    <li>Ensure ArUco tracker is running on ${trackerHost}</li>
                    <li>Check that port ${port} is open and accessible</li>
                    <li>Verify network connectivity between Foundry and tracker</li>
                    <li>Check firewall settings on both machines</li>
                    <li>Make sure ArUco markers are properly generated and printed</li>
                </ul>
            </div>
        `;
        
        new Dialog({
            title: "ArUco Tracker Status",
            content: content,
            buttons: {
                close: {
                    label: "Close"
                }
            },
            default: "close"
        }).render(true);
    }

    reconnect() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.isConnected = false;
        this.lastConnectionAttempt = new Date().toLocaleString();
        setTimeout(() => this.connectWebSocket(), 1000);
    }

    async testConnection() {
        const trackerHost = game.settings.get("aruco-tracker", "trackerHost");
        const port = game.settings.get("aruco-tracker", "websocketPort");
        
        ui.notifications.info(`Testing connection to ${trackerHost}:${port}...`);
        
        try {
            // Test basic connectivity with a temporary WebSocket
            const testWs = new WebSocket(`ws://${trackerHost}:${port}`);
            
            const testPromise = new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    testWs.close();
                    reject(new Error('Connection timeout'));
                }, 5000);
                
                testWs.onopen = () => {
                    clearTimeout(timeout);
                    testWs.close();
                    resolve('Connection successful');
                };
                
                testWs.onerror = (error) => {
                    clearTimeout(timeout);
                    reject(error);
                };
            });
            
            await testPromise;
            ui.notifications.info(`✓ Connection test successful to ${trackerHost}:${port}`);
            
        } catch (error) {
            console.error('Connection test failed:', error);
            ui.notifications.error(`✗ Connection test failed: ${error.message}`);
            
            // Provide specific guidance based on error
            if (error.message.includes('timeout')) {
                ui.notifications.warn('Check if ArUco tracker is running and accessible from this network');
            }
        }
    }

    cleanup() {
        if (this.websocket) {
            this.websocket.close();
        }
        this.isConnected = false;
        this.tokenCache.clear();
    }
}

// Initialize the module
let arucoTracker = null;

Hooks.once('init', () => {
    console.log("ArUco Tracker | Module initializing");
    arucoTracker = new ArucoTrackerModule();
});

Hooks.once('ready', () => {
    arucoTracker.initialize();
    
    // Expose API for console access
    game.modules.get('aruco-tracker').api = {
        reconnect: () => arucoTracker.reconnect(),
        testConnection: () => arucoTracker.testConnection(),
        getStatus: () => ({
            connected: arucoTracker.isConnected,
            trackedTokens: arucoTracker.tokenCache.size,
            trackerHost: game.settings.get("aruco-tracker", "trackerHost"),
            websocketPort: game.settings.get("aruco-tracker", "websocketPort")
        }),
        getTrackedTokens: () => Array.from(arucoTracker.tokenCache.entries()),
        getMarkerSchema: () => arucoTracker.markerSchema
    };
});

Hooks.on('closeApplication', () => {
    if (arucoTracker) {
        arucoTracker.cleanup();
    }
});

// Export for module use
export { ArucoTrackerModule };