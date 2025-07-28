// Foundry VTT QR Tracker Module
// Place this in: Data/modules/qr-tracker/qr-tracker.js

class QRTrackerModule {
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
    }

    async initialize() {
        console.log("QR Tracker | Initializing module");
        
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
        game.settings.register("qr-tracker", "trackerHost", {
            name: "QR Tracker Host",
            hint: "IP address or hostname of the QR tracker (Raspberry Pi)",
            scope: "world",
            config: true,
            type: String,
            default: "localhost"
        });

        game.settings.register("qr-tracker", "websocketPort", {
            name: "WebSocket Port",
            hint: "Port for QR tracker WebSocket connection",
            scope: "world",
            config: true,
            type: Number,
            default: 30001
        });

        game.settings.register("qr-tracker", "autoCreateTokens", {
            name: "Auto-Create Tokens",
            hint: "Automatically create tokens for new QR codes",
            scope: "world",
            config: true,
            type: Boolean,
            default: true
        });

        game.settings.register("qr-tracker", "tokenImagePath", {
            name: "Default Token Image",
            hint: "Default image for auto-created tokens",
            scope: "world",
            config: true,
            type: String,
            default: "icons/svg/mystery-man.svg"
        });

        game.settings.register("qr-tracker", "enableCORS", {
            name: "Enable CORS Headers",
            hint: "Add CORS headers for cross-origin requests from tracker",
            scope: "world",
            config: true,
            type: Boolean,
            default: true
        });
    }

    connectWebSocket() {
        const trackerHost = game.settings.get("qr-tracker", "trackerHost");
        const port = game.settings.get("qr-tracker", "websocketPort");
        const wsUrl = `ws://${trackerHost}:${port}`;
        
        console.log(`QR Tracker | Attempting connection to: ${wsUrl}`);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log("QR Tracker | WebSocket connected to remote tracker");
                this.isConnected = true;
                ui.notifications.info(`QR Tracker connected to ${trackerHost}`);
                
                // Send handshake with Foundry info
                this.websocket.send(JSON.stringify({
                    type: "foundry_ready",
                    scene_id: game.scenes.active?.id,
                    foundry_host: window.location.hostname,
                    foundry_port: window.location.port || 30000,
                    user_id: game.user.id,
                    timestamp: Date.now()
                }));
            };
            
            this.websocket.onmessage = (event) => {
                this.handleWebSocketMessage(JSON.parse(event.data));
            };
            
            this.websocket.onclose = (event) => {
                console.log(`QR Tracker | WebSocket disconnected (Code: ${event.code})`);
                this.isConnected = false;
                
                if (event.code !== 1000) { // Not a normal closure
                    ui.notifications.warn(`QR Tracker disconnected from ${trackerHost}`);
                }
                
                // Attempt reconnection for non-intentional disconnects
                if (event.code !== 1000 && event.code !== 1001) {
                    setTimeout(() => {
                        if (!this.isConnected) {
                            console.log("QR Tracker | Attempting reconnection...");
                            this.connectWebSocket();
                        }
                    }, this.config.reconnectInterval);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error("QR Tracker | WebSocket error:", error);
                ui.notifications.error(`Failed to connect to QR tracker at ${trackerHost}:${port}`);
            };
            
        } catch (error) {
            console.error("QR Tracker | Failed to create WebSocket connection:", error);
            ui.notifications.error(`Cannot connect to QR tracker: ${error.message}`);
        }
    }

    async handleWebSocketMessage(data) {
        switch (data.type) {
            case "token_update":
                await this.updateTokenPosition(data);
                break;
            case "handshake":
                console.log("QR Tracker | Received handshake from tracker");
                break;
            default:
                console.log("QR Tracker | Unknown message type:", data.type);
        }
    }

    async updateTokenPosition(data) {
        const { qr_id, token_id, x, y, confidence, scene_id } = data;
        
        // Check if this is for the current scene
        if (scene_id && scene_id !== game.scenes.active?.id) {
            return;
        }
        
        // Throttle updates
        const now = Date.now();
        const lastUpdate = this.lastUpdate[qr_id] || 0;
        if (now - lastUpdate < this.config.updateThrottle) {
            return;
        }
        this.lastUpdate[qr_id] = now;
        
        try {
            let token = null;
            
            // Find token by ID or QR mapping
            if (token_id) {
                token = game.scenes.active.tokens.get(token_id);
            }
            
            if (!token) {
                // Look for token by QR ID in flags
                token = game.scenes.active.tokens.find(t => 
                    t.getFlag("qr-tracker", "qr_id") === qr_id
                );
            }
            
            if (!token) {
                // Create new token if auto-create is enabled
                if (game.settings.get("qr-tracker", "autoCreateTokens")) {
                    token = await this.createTokenForQR(qr_id, x, y);
                } else {
                    console.warn(`QR Tracker | No token found for QR ID: ${qr_id}`);
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
                this.tokenCache.set(qr_id, {
                    tokenId: token.id,
                    lastSeen: now,
                    confidence: confidence
                });
                
                console.log(`QR Tracker | Updated token ${token.name} to (${x}, ${y})`);
            }
            
        } catch (error) {
            console.error("QR Tracker | Error updating token:", error);
        }
    }

    async createTokenForQR(qr_id, x, y) {
        const tokenImage = game.settings.get("qr-tracker", "tokenImagePath");
        
        const tokenData = {
            name: `Player_${qr_id}`,
            img: tokenImage,
            x: x,
            y: y,
            width: 1,
            height: 1,
            flags: {
                "qr-tracker": {
                    qr_id: qr_id,
                    created_by_tracker: true,
                    created_at: Date.now()
                }
            }
        };
        
        try {
            const tokenDocument = await game.scenes.active.createEmbeddedDocuments("Token", [tokenData]);
            const token = tokenDocument[0];
            
            ui.notifications.info(`Created token for QR: ${qr_id}`);
            console.log(`QR Tracker | Created token for QR ${qr_id}:`, token);
            
            return token;
        } catch (error) {
            console.error("QR Tracker | Failed to create token:", error);
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
                const response = await fetch('/modules/qr-tracker/token_data.json');
                if (response.ok) {
                    const data = await response.json();
                    await this.processFileData(data);
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
                qr_id: tokenData.qr_id,
                token_id: tokenData.foundry_token_id,
                x: tokenData.x,
                y: tokenData.y,
                confidence: tokenData.confidence,
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
                    name: "qr-tracker-status",
                    title: "QR Tracker Status",
                    icon: this.isConnected ? "fas fa-wifi" : "fas fa-exclamation-triangle",
                    onClick: () => this.showStatusDialog(),
                    button: true
                });
            }
        });
    }

    showStatusDialog() {
        const trackerHost = game.settings.get("qr-tracker", "trackerHost");
        const port = game.settings.get("qr-tracker", "websocketPort");
        
        const content = `
            <div>
                <h3>QR Tracker Status</h3>
                <p><strong>Tracker Host:</strong> ${trackerHost}:${port}</p>
                <p><strong>Connection:</strong> ${this.isConnected ? 'Connected ✓' : 'Disconnected ✗'}</p>
                <p><strong>Tracked Tokens:</strong> ${this.tokenCache.size}</p>
                <p><strong>Active Scene:</strong> ${game.scenes.active?.name || 'None'}</p>
                <p><strong>Foundry Host:</strong> ${window.location.hostname}:${window.location.port || 30000}</p>
                
                <h4>Network Diagnostics:</h4>
                <p><strong>WebSocket URL:</strong> ws://${trackerHost}:${port}</p>
                <p><strong>Last Connection Attempt:</strong> ${this.lastConnectionAttempt || 'Never'}</p>
                
                <h4>Tracked QR Codes:</h4>
                ${this.tokenCache.size > 0 ? `
                    <ul>
                        ${Array.from(this.tokenCache.entries()).map(([qrId, data]) => 
                            `<li>${qrId} (Confidence: ${data.confidence?.toFixed(2) || 'N/A'}, Last seen: ${new Date(data.lastSeen).toLocaleTimeString()})</li>`
                        ).join('')}
                    </ul>
                ` : '<p><em>No QR codes currently tracked</em></p>'}
                
                <div style="margin-top: 15px;">
                    <button type="button" onclick="game.modules.get('qr-tracker').api.reconnect()">
                        Reconnect to Tracker
                    </button>
                    <button type="button" onclick="game.modules.get('qr-tracker').api.testConnection()">
                        Test Connection
                    </button>
                </div>
                
                <h4>Troubleshooting:</h4>
                <ul style="font-size: 0.9em;">
                    <li>Ensure QR tracker is running on ${trackerHost}</li>
                    <li>Check that port ${port} is open and accessible</li>
                    <li>Verify network connectivity between Foundry and tracker</li>
                    <li>Check firewall settings on both machines</li>
                </ul>
            </div>
        `;
        
        new Dialog({
            title: "QR Tracker Status",
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
        const trackerHost = game.settings.get("qr-tracker", "trackerHost");
        const port = game.settings.get("qr-tracker", "websocketPort");
        
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
                ui.notifications.warn('Check if QR tracker is running and accessible from this network');
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
let qrTracker = null;

Hooks.once('init', () => {
    console.log("QR Tracker | Module initializing");
    qrTracker = new QRTrackerModule();
});

Hooks.once('ready', () => {
    qrTracker.initialize();
    
    // Expose API for console access
    game.modules.get('qr-tracker').api = {
        reconnect: () => qrTracker.reconnect(),
        testConnection: () => qrTracker.testConnection(),
        getStatus: () => ({
            connected: qrTracker.isConnected,
            trackedTokens: qrTracker.tokenCache.size,
            trackerHost: game.settings.get("qr-tracker", "trackerHost"),
            websocketPort: game.settings.get("qr-tracker", "websocketPort")
        }),
        getTrackedTokens: () => Array.from(qrTracker.tokenCache.entries())
    };
});

Hooks.on('closeApplication', () => {
    if (qrTracker) {
        qrTracker.cleanup();
    }
});

// Export for module use
export { QRTrackerModule };