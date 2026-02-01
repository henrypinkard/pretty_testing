#!/bin/bash

# CHANGE: Use current directory (pwd) instead of $HOME
INSTALL_DIR="$(pwd)/pretty_testing"

# Clone if it doesn't exist, pull if it does
if [ -d "$INSTALL_DIR" ]; then
    echo "Updating pretty_testing in current directory..."
    git -C "$INSTALL_DIR" pull
else
    echo "Cloning pretty_testing into current directory..."
    git clone --depth 1 https://github.com/henrypinkard/pretty_testing.git "$INSTALL_DIR"
fi

# Run the setup script
source "$INSTALL_DIR/setup.sh"