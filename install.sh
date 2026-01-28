#!/bin/bash

# Define where to install
INSTALL_DIR="$HOME/pretty_testing"

# Clone if it doesn't exist, pull if it does
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating pretty_testing..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning pretty_testing..."
    git clone https://github.com/henrypinkard/pretty_testing.git "$INSTALL_DIR"
fi

# Run the setup script to configure aliases permanently
source "$INSTALL_DIR/setup.sh"