#!/bin/bash

# Install system libraries needed for audio
sudo apt-get update
sudo apt-get install -y libasound2-dev mpv libmpv-dev

pip install .