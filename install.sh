#!/bin/bash

INSTALL_DIR="$(pwd)/pretty_testing"

# Clean install every time — no stale state
# If .git exists with immutable pack files (from old git clone install),
# we can't delete it without root. Delete everything else and work around it.
if [ -d "$INSTALL_DIR" ]; then
    find "$INSTALL_DIR" -maxdepth 1 -not -name '.git' -not -path "$INSTALL_DIR" -exec rm -rf {} + 2>/dev/null
    rm -rf "$INSTALL_DIR/.git" 2>/dev/null  # try anyway; harmless if it fails
fi

# Download latest as tarball (no git needed, no .git directory)
echo "Installing pretty_testing..."
mkdir -p "$INSTALL_DIR"
curl -sL https://github.com/henrypinkard/pretty_testing/archive/refs/heads/main.tar.gz \
    | tar xz --strip-components=1 -C "$INSTALL_DIR"

if [ ! -f "$INSTALL_DIR/setup.sh" ]; then
    echo "ERROR: Download failed. Check your internet connection."
    exit 1
fi

# Hide installed files from the parent project's git
echo '*' > "$INSTALL_DIR/.gitignore"

# Run the setup script
source "$INSTALL_DIR/setup.sh"
