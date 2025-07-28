#!/usr/bin/env python3
"""
Network Test Script for Foundry ArUco Token Tracker
==========================================

This script tests network connectivity between the Raspberry Pi
and the Foundry VTT host before running the full tracker.

Usage:
python3 network_test.py --foundry-host 192.168.1.50 --foundry-port 30000
"""

import asyncio
import websockets
import requests
import argparse
import socket
import time
from urllib.parse import urlparse


def test_basic_connectivity(host, timeout=5):
    """Test basic network connectivity via ping-like socket test."""
    print(f"Testing basic connectivity to {host}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, 80))  # Test with port 80
        sock.close()
        
        if result == 0:
            print("✓ Host is reachable")
            return True
        else:
            print("✗ Host is not reachable")
            return False
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False


def test_foundry_http(foundry_url, timeout=10):
    """Test Foundry HTTP API accessibility."""
    print(f"Testing Foundry HTTP API at {foundry_url}...")
    try:
        response = requests.get(f"{foundry_url}/api/status", timeout=timeout)
        if response.status_code == 200:
            print("✓ Foundry HTTP API is accessible")
            return True
        else:
            print(f"⚠ Foundry HTTP returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectTimeout:
        print("✗ Connection to Foundry timed out")
        return False
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to Foundry")
        return False
    except Exception as e:
        print(f"✗ HTTP test failed: {e}")
        return False


def test_websocket_port(host, port, timeout=10):
    """Test if WebSocket port is accessible."""
    print(f"Testing WebSocket port {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print("✓ WebSocket port is open")
            return True
        else:
            print("✗ WebSocket port is closed or filtered")
            return False
    except Exception as e:
        print(f"✗ WebSocket port test failed: {e}")
        return False


async def test_websocket_server(port, duration=30):
    """Start a simple WebSocket server to test Foundry can connect back."""
    print(f"Starting test WebSocket server on port {port} for {duration} seconds...")
    print("Now try connecting from Foundry module or test with:")
    print(f"  wscat -c ws://$(hostname -I | awk '{{print $1}}'):{port}")
    
    connections = set()
    
    async def handle_client(websocket, path):
        print(f"✓ Client connected from {websocket.remote_address}")
        connections.add(websocket)
        try:
            await websocket.send("Hello from AruCo Token Tracker test server!")
            async for message in websocket:
                print(f"Received: {message}")
                await websocket.send(f"Echo: {message}")
        except websockets.exceptions.ConnectionClosed:
            print(f"Client {websocket.remote_address} disconnected")
        finally:
            connections.discard(websocket)
    
    try:
        server = await websockets.serve(handle_client, "0.0.0.0", port)
        print(f"✓ WebSocket server started on port {port}")
        
        # Wait for the specified duration
        await asyncio.sleep(duration)
        
        print(f"Test server stopping after {duration} seconds")
        server.close()
        await server.wait_closed()
        
        if connections:
            print(f"✓ Successfully handled {len(connections)} connection(s)")
        else:
            print("⚠ No connections were received during test")
            
    except Exception as e:
        print(f"✗ Failed to start WebSocket server: {e}")


def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to a remote address to determine local IP
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        local_ip = sock.getsockname()[0]
        sock.close()
        return local_ip
    except Exception:
        return "localhost"


async def main():
    parser = argparse.ArgumentParser(description="Test network connectivity for Foundry ArUco Token Tracker")
    parser.add_argument("--foundry-host", required=True, help="Foundry VTT host IP or hostname")
    parser.add_argument("--foundry-port", type=int, default=30000, help="Foundry VTT port")
    parser.add_argument("--websocket-port", type=int, default=30001, help="WebSocket port for testing")
    parser.add_argument("--test-server", action="store_true", help="Start test WebSocket server")
    parser.add_argument("--server-duration", type=int, default=30, help="How long to run test server (seconds)")
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("Foundry ArUco Token Tracker Network Test")
    print("=" * 60)
    print(f"Local IP: {get_local_ip()}")
    print(f"Target Foundry Host: {args.foundry_host}:{args.foundry_port}")
    print(f"WebSocket Port: {args.websocket_port}")
    print("-" * 60)
    
    # Test 1: Basic connectivity
    connectivity_ok = test_basic_connectivity(args.foundry_host)
    
    # Test 2: Foundry HTTP API
    foundry_url = f"http://{args.foundry_host}:{args.foundry_port}"
    http_ok = test_foundry_http(foundry_url)
    
    # Test 3: WebSocket port accessibility
    websocket_ok = test_websocket_port(args.foundry_host, args.websocket_port)
    
    print("-" * 60)
    
    if connectivity_ok and http_ok:
        print("✓ Network connectivity looks good!")
        print("You should be able to run the ArUco Token Tracker with:")
        print(f"  python3 foundry_qr_tracker.py --foundry-url {foundry_url} --scene-id YOUR_SCENE_ID")
    else:
        print("✗ Network issues detected:")
        if not connectivity_ok:
            print("  - Cannot reach Foundry host")
        if not http_ok:
            print("  - Cannot access Foundry HTTP API")
        if not websocket_ok:
            print("  - WebSocket port may not be accessible")
        
        print("\nTroubleshooting suggestions:")
        print("1. Check that both machines are on the same network")
        print("2. Verify Foundry is running and accessible")
        print("3. Check firewall settings on both machines")
        print(f"4. Ensure port {args.websocket_port} is open")
    
    # Optional: Start test WebSocket server
    if args.test_server:
        print("-" * 60)
        await test_websocket_server(args.websocket_port, args.server_duration)
    
    print("-" * 60)
    print("Network test complete!")


if __name__ == "__main__":
    asyncio.run(main())
