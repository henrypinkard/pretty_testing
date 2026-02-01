#!/bin/bash

INSTALL_DIR="$(pwd)/pretty_testing"

# Clean install every time — no stale state
rm -rf "$INSTALL_DIR"

# Download latest as tarball (no git needed, no .git directory)
echo "Installing pretty_testing..."
mkdir -p "$INSTALL_DIR"
curl -sL https://github.com/henrypinkard/pretty_testing/archive/refs/heads/main.tar.gz \
    | tar xz --strip-components=1 -C "$INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/setup.sh" ]; then
    echo "ERROR: Download failed. Check your internet connection."
    exit 1
fi

# Run the setup script
source "$INSTALL_DIR/setup.sh"
