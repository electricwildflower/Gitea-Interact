#!/bin/bash

# Gitea-Interact Dependencies Installation Script
# Run this script if you encounter dependency issues after installing the .deb package

echo "Installing Gitea-Interact Python dependencies..."

# Check if we're running as root
if [ "$EUID" -eq 0 ]; then
    echo "Running as root. Installing dependencies with --break-system-packages flag..."
    pip3 install -r /usr/share/gitea-interact/requirements.txt --break-system-packages
else
    echo "Installing dependencies for current user..."
    pip3 install -r /usr/share/gitea-interact/requirements.txt --user
fi

echo "Dependencies installation completed!"
echo "You can now run 'gitea-interact' from the command line."
