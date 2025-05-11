#!/bin/bash

# Detect package manager
if command -v apt-get &> /dev/null; then
    echo "Using apt-get (Debian/Ubuntu)"
    sudo apt-get update
    sudo apt-get install -y libasound2-dev mpv
elif command -v dnf &> /dev/null; then
    echo "Using dnf (Fedora)"
    sudo dnf install -y alsa-lib-devel mpv
else
    echo "Unsupported package manager. Please install dependencies manually."
    exit 1
fi

# Install Python package
pip install .
