@echo off
setlocal enabledelayedexpansion

REM Mock FoundryVTT Server Setup Script for Windows
REM Automatically creates virtual environment and installs dependencies

set "VENV_NAME=foundry-server-env"
set "PROJECT_NAME=Mock FoundryVTT Server"
set "SERVER_SCRIPT=mock_foundry_server.py"

echo ================================
echo 🎲 %PROJECT_NAME% Setup
echo ================================
echo.

REM Check if Python is installed
echo [INFO] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo [ERROR] Please install Python 3.7+ from https://python.org
    echo [ERROR] Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
echo [INFO] Found Python %PYTHON_VERSION%

REM Check if virtual environment already exists
if exist "%VENV_NAME%" (
    echo [WARNING] Virtual environment '%VENV_NAME%' already exists
    set /p "REPLY=Do you want to remove it and create a new one? (y/N): "
    if /i "!REPLY!"=="y" (
        echo [INFO] Removing existing virtual environment...
        rmdir /s /q "%VENV_NAME%"
    ) else (
        echo [INFO] Using existing virtual environment
        if not exist "%VENV_NAME%\Scripts\activate.bat" (
            echo [ERROR] Existing virtual environment is corrupted
            echo [ERROR] Please remove the '%VENV_NAME%' directory and run this script again
            pause
            exit /b 1
        )
    )
)

REM Create virtual environment if it doesn't exist
if not exist "%VENV_NAME%" (
    echo [INFO] Creating virtual environment '%VENV_NAME%'...
    python -m venv "%VENV_NAME%"
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo [ERROR] Make sure you have Python 3.7+ installed properly
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created successfully
)

REM Check if requirements.txt exists
if not exist "requirements.txt" (
    echo [WARNING] requirements.txt not found, creating minimal requirements...
    (
        echo # Mock FoundryVTT Server Dependencies
        echo # Advanced async server using aiohttp and websockets
        echo #
        echo # RECOMMENDED: Use a virtual environment to avoid conflicts
        echo # 
        echo # Setup virtual environment:
        echo #   python3 -m venv foundry-server-env
        echo #   source foundry-server-env/bin/activate  # Linux/Mac
        echo #   foundry-server-env\Scripts\activate     # Windows
        echo #
        echo # Install dependencies:
        echo #   pip install -r requirements.txt
        echo #
        echo # Run the server ^(while virtual environment is active^):
        echo #   python3 mock_foundry_server.py --verbose
        echo #
        echo # Deactivate when done:
        echo #   deactivate
        echo.
        echo # Core HTTP server framework
        echo aiohttp^>=3.8.0
        echo.
        echo # WebSocket server support
        echo websockets^>=10.0
        echo.
        echo # Optional: Enhanced async HTTP client capabilities
        echo aiohttp[speedups]^>=3.8.0
        echo.
        echo # Note: All other dependencies are part of Python standard library:
        echo # - asyncio ^(Python 3.7+^)
        echo # - json
        echo # - logging  
        echo # - time
        echo # - uuid
        echo # - datetime
        echo # - pathlib
        echo # - typing
        echo # - argparse
    ) > requirements.txt
    echo [SUCCESS] Created requirements.txt
)

REM Install dependencies
echo [INFO] Installing dependencies...
call "%VENV_NAME%\Scripts\activate.bat" && (
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) || (
    echo [ERROR] Failed to install dependencies
    echo [ERROR] Try running manually:
    echo [ERROR]   %VENV_NAME%\Scripts\activate.bat
    echo [ERROR]   pip install -r requirements.txt
    pause
    exit /b 1
)

echo [SUCCESS] Dependencies installed successfully

REM Check if main server script exists
if not exist "%SERVER_SCRIPT%" (
    echo [WARNING] Server script '%SERVER_SCRIPT%' not found in current directory
    echo [WARNING] Make sure to copy the server script here before running
)

REM Print completion message and instructions
echo.
echo [SUCCESS] Setup completed successfully!
echo.
echo 🚀 Next Steps:
echo.
echo 1. Activate the virtual environment:
echo    %VENV_NAME%\Scripts\activate.bat
echo.
echo 2. Run the mock server:
echo    python %SERVER_SCRIPT%
echo    python %SERVER_SCRIPT% --verbose
echo    python %SERVER_SCRIPT% --port 8000 --ws-port 8001
echo.
echo 3. Access the web interface:
echo    http://localhost:30000
echo    http://your-pc-ip:30000
echo.
echo 4. When finished, deactivate:
echo    deactivate
echo.
echo 📁 Files created:
echo    📂 %VENV_NAME%\          (virtual environment)
echo    📄 requirements.txt     (dependencies)

if exist "%SERVER_SCRIPT%" (
    echo    📄 %SERVER_SCRIPT%   (✅ ready to run)
) else (
    echo    📄 %SERVER_SCRIPT%   (❌ copy this file here)
)

echo.
echo 🔧 Quick Start Command:
echo %VENV_NAME%\Scripts\activate.bat ^&^& python %SERVER_SCRIPT% --verbose
echo.
echo [SUCCESS] Happy testing! 🎲✨
echo.
pause