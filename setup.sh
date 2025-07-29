#!/bin/bash
""" # Setup local virtual environment """
sudo apt install python3-venv
python3 -m venv .venv
cd .venv
source bin/activate
cd ..
"""# Install Python packages into virtual environment (req'd in Debian 12 "Bookworm")
 # (pip won't let us install without doing this) """
pip install -r project_dependencies.txt