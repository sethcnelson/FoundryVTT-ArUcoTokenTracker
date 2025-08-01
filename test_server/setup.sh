#!/bin/bash

# Mock FoundryVTT Server Setup Script
# Automatically creates virtual environment and installs dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
VENV_NAME="foundry-server-env"
PROJECT_NAME="Mock FoundryVTT Server"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${PURPLE}================================${NC}"
    echo -e "${PURPLE}🎲 $PROJECT_NAME Setup${NC}"
    echo -e "${PURPLE}================================${NC}"
    echo
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python version
get_python_version() {
    if command_exists python3; then
        python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    else
        echo "0.0"
    fi
}

# Function to check Python version compatibility
check_python_version() {
    local version=$(get_python_version)
    local major=$(echo $version | cut -d. -f1)
    local minor=$(echo $version | cut -d. -f2)
    
    if [[ $major -ge 3 && $minor -ge 7 ]]; then
        return 0
    else
        return 1
    fi
}

# Main setup function
main() {
    print_header
    
    # Check if Python3 is installed
    print_status "Checking Python installation..."
    if ! command_exists python3; then
        print_error "Python3 is not installed or not in PATH"
        print_error "Please install Python 3.7+ before running this script"
        print_error "On Raspberry Pi: sudo apt update && sudo apt install python3 python3-pip python3-venv"
        exit 1
    fi
    
    # Check Python version
    local python_version=$(get_python_version)
    print_status "Found Python $python_version"
    
    if ! check_python_version; then
        print_error "Python 3.7+ is required (found $python_version)"
        print_error "Please upgrade Python before proceeding"
        exit 1
    fi
    
    print_success "Python version is compatible"
    
    # Check if virtual environment already exists
    if [[ -d "$VENV_NAME" ]]; then
        print_warning "Virtual environment '$VENV_NAME' already exists"
        read -p "Do you want to remove it and create a new one? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_status "Removing existing virtual environment..."
            rm -rf "$VENV_NAME"
        else
            print_status "Using existing virtual environment"
            if [[ ! -f "$VENV_NAME/bin/activate" && ! -f "$VENV_NAME/Scripts/activate" ]]; then
                print_error "Existing virtual environment is corrupted"
                print_error "Please remove the '$VENV_NAME' directory and run this script again"
                exit 1
            fi
        fi
    fi
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "$VENV_NAME" ]]; then
        print_status "Creating virtual environment '$VENV_NAME'..."
        if ! python3 -m venv "$VENV_NAME"; then
            print_error "Failed to create virtual environment"
            print_error "Make sure python3-venv is installed: sudo apt install python3-venv"
            exit 1
        fi
        print_success "Virtual environment created successfully"
    fi
    
    # Determine activation script path
    if [[ -f "$VENV_NAME/bin/activate" ]]; then
        ACTIVATE_PATH="$VENV_NAME/bin/activate"
        PLATFORM="unix"
    elif [[ -f "$VENV_NAME/Scripts/activate" ]]; then
        ACTIVATE_PATH="$VENV_NAME/Scripts/activate"
        PLATFORM="windows"
    else
        print_error "Could not find activation script in virtual environment"
        exit 1
    fi
    
    # Check if requirements.txt exists
    if [[ ! -f "requirements.txt" ]]; then
        print_warning "requirements.txt not found, creating minimal requirements..."
        cat > requirements.txt << EOF
# Mock FoundryVTT Server Dependencies
# Advanced async server using aiohttp and websockets
#
# RECOMMENDED: Use a virtual environment to avoid conflicts
# 
# Setup virtual environment:
#   python3 -m venv foundry-server-env
#   source foundry-server-env/bin/activate  # Linux/Mac
#   foundry-server-env\\Scripts\\activate     # Windows
#
# Install dependencies:
#   pip install -r requirements.txt
#
# Run the server (while virtual environment is active):
#   python3 mock_foundry_server.py --verbose
#
# Deactivate when done:
#   deactivate

# Core HTTP server framework
aiohttp>=3.8.0

# WebSocket server support
websockets>=10.0

# Optional: Enhanced async HTTP client capabilities
aiohttp[speedups]>=3.8.0

# Note: All other dependencies are part of Python standard library:
# - asyncio (Python 3.7+)
# - json
# - logging  
# - time
# - uuid
# - datetime
# - pathlib
# - typing
# - argparse
EOF
        print_success "Created requirements.txt"
    fi
    
    # Activate virtual environment and install dependencies
    print_status "Installing dependencies..."
    
    # Create a temporary script to run in the virtual environment
    cat > temp_install.sh << EOF
#!/bin/bash
source "$ACTIVATE_PATH"
pip install --upgrade pip
pip install -r requirements.txt
EOF
    
    if bash temp_install.sh; then
        print_success "Dependencies installed successfully"
    else
        print_error "Failed to install dependencies"
        print_error "Try running manually:"
        print_error "  source $ACTIVATE_PATH"
        print_error "  pip install -r requirements.txt"
        rm -f temp_install.sh
        exit 1
    fi
    
    # Clean up temporary script
    rm -f temp_install.sh
    
    # Check if main server script exists
    SERVER_SCRIPT="mock_foundry_server.py"
    if [[ ! -f "$SERVER_SCRIPT" ]]; then
        print_warning "Server script '$SERVER_SCRIPT' not found in current directory"
        print_warning "Make sure to copy the server script here before running"
    fi
    
    # Print completion message and instructions
    echo
    print_success "Setup completed successfully!"
    echo
    echo -e "${PURPLE}🚀 Next Steps:${NC}"
    echo
    
    if [[ "$PLATFORM" == "unix" ]]; then
        echo -e "${GREEN}1. Activate the virtual environment:${NC}"
        echo -e "   ${YELLOW}source $ACTIVATE_PATH${NC}"
    else
        echo -e "${GREEN}1. Activate the virtual environment:${NC}"
        echo -e "   ${YELLOW}$VENV_NAME\\Scripts\\activate${NC}"
    fi
    
    echo
    echo -e "${GREEN}2. Run the mock server:${NC}"
    echo -e "   ${YELLOW}python3 $SERVER_SCRIPT${NC}"
    echo -e "   ${YELLOW}python3 $SERVER_SCRIPT --verbose${NC}"
    echo -e "   ${YELLOW}python3 $SERVER_SCRIPT --port 8000 --ws-port 8001${NC}"
    
    echo
    echo -e "${GREEN}3. Access the web interface:${NC}"
    echo -e "   ${YELLOW}http://localhost:30000${NC}"
    echo -e "   ${YELLOW}http://your-pi-ip:30000${NC}"
    
    echo
    echo -e "${GREEN}4. When finished, deactivate:${NC}"
    echo -e "   ${YELLOW}deactivate${NC}"
    
    echo
    echo -e "${BLUE}📁 Files created:${NC}"
    echo -e "   📂 $VENV_NAME/          (virtual environment)"
    echo -e "   📄 requirements.txt     (dependencies)"
    
    if [[ -f "$SERVER_SCRIPT" ]]; then
        echo -e "   📄 $SERVER_SCRIPT   (✅ ready to run)"
    else
        echo -e "   📄 $SERVER_SCRIPT   (❌ copy this file here)"
    fi
    
    echo
    echo -e "${PURPLE}🔧 Quick Start Command:${NC}"
    if [[ "$PLATFORM" == "unix" ]]; then
        echo -e "${YELLOW}source $ACTIVATE_PATH && python3 $SERVER_SCRIPT --verbose${NC}"
    else
        echo -e "${YELLOW}$VENV_NAME\\Scripts\\activate && python3 $SERVER_SCRIPT --verbose${NC}"
    fi
    
    echo
    print_success "Happy testing! 🎲✨"
}

# Help function
show_help() {
    echo "Mock FoundryVTT Server Setup Script"
    echo
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -c, --clean    Remove existing virtual environment before setup"
    echo
    echo "This script will:"
    echo "  1. Check Python 3.7+ installation"
    echo "  2. Create virtual environment '$VENV_NAME'"
    echo "  3. Install dependencies from requirements.txt"
    echo "  4. Provide instructions for running the server"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -c|--clean)
            if [[ -d "$VENV_NAME" ]]; then
                print_status "Removing existing virtual environment..."
                rm -rf "$VENV_NAME"
                print_success "Cleaned up existing environment"
            fi
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use -h or --help for usage information"
            exit 1
            ;;
    esac
done

# Run main function
main