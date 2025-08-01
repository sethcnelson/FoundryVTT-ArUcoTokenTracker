#!/usr/bin/env python3
"""
OpenCV ArUco Compatibility Checker
==================================

This script checks your OpenCV installation and determines which ArUco API
version is available. This helps troubleshoot compatibility issues.

Usage: python3 check_opencv.py
"""

import sys

def check_opencv():
    """Check OpenCV installation and ArUco compatibility."""
    print("OpenCV ArUco Compatibility Checker")
    print("=" * 40)
    
    # Test basic OpenCV import
    try:
        import cv2
        print(f"✓ OpenCV imported successfully")
        opencv_version = cv2.__version__
        print(f"  Version: {opencv_version}")
        
        # Parse version components
        version_parts = opencv_version.split('.')
        opencv_major = int(version_parts[0])
        opencv_minor = int(version_parts[1])
        opencv_patch = int(version_parts[2]) if len(version_parts) > 2 else 0
        
        print(f"  Parsed: {opencv_major}.{opencv_minor}.{opencv_patch}")
        
    except ImportError as e:
        print(f"✗ Failed to import OpenCV: {e}")
        print("\nSolutions:")
        print("  pip3 install opencv-python")
        print("  sudo apt install python3-opencv  # (Raspberry Pi)")
        return False
    except Exception as e:
        print(f"✗ Unexpected error importing OpenCV: {e}")
        return False
    
    # Test ArUco module availability
    try:
        # Test dictionary access
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
        print(f"✓ ArUco module available")
        print(f"  Dictionary DICT_6X6_250: {dictionary.markerSize} markers")
        
    except AttributeError as e:
        print(f"✗ ArUco module not available: {e}")
        print("\nSolutions:")
        print("  pip3 install opencv-contrib-python")
        print("  sudo apt install python3-opencv  # (includes ArUco)")
        return False
    except Exception as e:
        print(f"✗ Error accessing ArUco: {e}")
        return False
    
    # Determine API version
    print("\nArUco API Compatibility:")
    api_version = "legacy"

    # Check for new API (OpenCV 4.7+)
    if opencv_major > 4 or (opencv_major == 4 and opencv_minor >= 7):
        try:
            parameters = cv2.aruco.DetectorParameters()
            print(f"✓ ArUco DetectorParameters() available (newer API)")
            detector = cv2.aruco.ArucoDetector(dictionary, parameters)
            print(f"✓ New ArUco API available (OpenCV 4.7+)")
            print(f"  Using: cv2.aruco.ArucoDetector() class")
            api_version = "new"
        except AttributeError:
            print(f"⚠ New API expected but not available")
            print(f"  Falling back to legacy API")
            parameters = cv2.aruco.DetectorParameters_create()
            print(f"✓ ArUco DetectorParameters_create() available (older API)")
            api_version = "legacy"
        except Exception as e:
            print(f"✗ Error with new API: {e}")
            parameters = cv2.aruco.DetectorParameters_create()
            print(f"✓ ArUco DetectorParameters_create() available (older API)")
            api_version = "legacy"
    else:
        print(f"✓ Legacy ArUco API (OpenCV < 4.7)")
        parameters = cv2.aruco.DetectorParameters_create()
        print(f"✓ ArUco DetectorParameters_create() available (older API)")
        print(f"  Using: cv2.aruco.detectMarkers() function")
        api_version = "legacy"
    
    # Initialize generation_api variable
    generation_api = "legacy"  # Default value
    
    # Test actual detection (without camera)
    print("\nTesting marker detection...")
    try:
        import numpy as np
        
        # Create a simple test image
        test_image = np.ones((400, 400), dtype=np.uint8) * 255
        
        if api_version == "new":
            try:
                corners, ids, rejected = detector.detectMarkers(test_image)
                print(f"✓ New API detection test successful")
            except Exception as e:
                print(f"✗ New API detection failed: {e}")
                api_version = "legacy"
        
        if api_version == "legacy":
            corners, ids, rejected = cv2.aruco.detectMarkers(
                image=test_image, dictionary=dictionary, parameters=parameters)
            print(f"✓ Legacy API detection test successful")
            
    except Exception as e:
        print(f"✗ Detection test failed: {e}")
        return False
    
    # Test marker generation
    print("\nTesting marker generation...")
    try:
        test_marker_id = 10
        marker_size = 100
        
        if opencv_major > 4 or (opencv_major == 4 and opencv_minor >= 7):
            # Try new API first
            try:
                marker_image = cv2.aruco.generateImageMarker(
                    dictionary, test_marker_id, marker_size, borderBits=1)
                print(f"✓ New API marker generation successful")
                generation_api = "new"
            except AttributeError:
                # Fall back to legacy API
                marker_image = np.ones((marker_size, marker_size), dtype=np.uint8) * 255
                cv2.aruco.drawMarker(dictionary, test_marker_id, marker_size, 
                                   marker_image, borderBits=1)
                print(f"✓ Legacy API marker generation successful (fallback)")
                generation_api = "legacy"
        else:
            # Use legacy API
            marker_image = np.ones((marker_size, marker_size), dtype=np.uint8) * 255
            cv2.aruco.drawMarker(dictionary, test_marker_id, marker_size, 
                               marker_image, borderBits=1)
            print(f"✓ Legacy API marker generation successful")
            generation_api = "legacy"
            
        # Verify the generated marker is valid
        if marker_image is not None and marker_image.shape == (marker_size, marker_size):
            print(f"✓ Generated marker has correct dimensions: {marker_image.shape}")
        else:
            print(f"✗ Generated marker has incorrect dimensions: {marker_image.shape if marker_image is not None else 'None'}")
            return False
            
    except Exception as e:
        print(f"✗ Marker generation test failed: {e}")
        return False
    
    # Summary
    print("\n" + "=" * 40)
    print("SUMMARY")
    print("=" * 40)
    print(f"OpenCV Version: {opencv_version}")
    print(f"ArUco Support: Available")
    print(f"Detection API: {api_version.title()}")
    print(f"Generation API: {generation_api.title()}")
    print(f"Compatibility: ✓ Compatible with ArUco Token Tracker")
    
    # Recommendations
    print("\nRecommendations:")
    if opencv_major == 4 and opencv_minor < 7:
        print("• Your OpenCV version uses the legacy ArUco APIs")
        print("• Detection: cv2.aruco.detectMarkers() function")
        print("• Generation: cv2.aruco.drawMarker() function")
        print("• Parameters: cv2.aruco.DetectorParameters_create() function")
        print("• This is common on Raspberry Pi OS and works perfectly")
        print("• The tracker automatically detects and uses the correct APIs")
    elif opencv_major >= 4 and opencv_minor >= 7:
        print("• Your OpenCV version supports the new ArUco APIs")
        print("• Detection: cv2.aruco.ArucoDetector() class")
        print("• Generation: cv2.aruco.generateImageMarker() function")
        print("• Parameters: cv2.aruco.DetectorParameters() function")
        print("• This provides slightly better performance")
        print("• The tracker will automatically use the new APIs")
    else:
        print("• Consider upgrading OpenCV for better ArUco support")
        print("• Minimum recommended: OpenCV 4.2+")
    
    return True

def show_installation_help():
    """Show installation help for common scenarios."""
    print("\n" + "=" * 40)
    print("INSTALLATION HELP")
    print("=" * 40)
    
    print("\nRaspberry Pi OS (Recommended):")
    print("  sudo apt update")
    print("  sudo apt install python3-opencv python3-numpy")
    print("  # ArUco support is included")
    
    print("\nUbuntu/Debian:")
    print("  sudo apt install python3-opencv python3-numpy")
    print("  # OR")
    print("  pip3 install opencv-python")
    
    print("\nIf ArUco is missing:")
    print("  pip3 install opencv-contrib-python")
    
    print("\nFor compilation issues:")
    print("  pip3 install opencv-python-headless")
    
    print("\nSpecific version for compatibility:")
    print("  pip3 install opencv-python==4.5.5.64")

if __name__ == "__main__":
    print("Checking OpenCV and ArUco compatibility...\n")
    
    success = check_opencv()
    
    if not success:
        show_installation_help()
        sys.exit(1)
    else:
        print(f"\n🎉 Your system is ready for ArUco token tracking!")
        print("\nNext steps:")
        print("  1. Generate markers: python3 aruco_generator.py --complete")
        print("  2. Test camera: python3 aruco_preview.py")
        print("  3. Start tracking: python3 foundry_aruco_tracker.py")
