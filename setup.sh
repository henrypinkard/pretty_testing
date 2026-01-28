#!/bin/bash

# 1. Get the absolute path to the folder where this script lives
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Make binaries executable
chmod +x "$KIT_ROOT/bin/"*

# 3. Detect which shell config file to use (Zsh vs Bash)
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
else
    SHELL_CONFIG="$HOME/.bashrc"
fi

# 4. Append aliases to the config file so they persist after restart
# We check grep first to ensure we don't add the same alias multiple times
echo "Configuring aliases in $SHELL_CONFIG..."

if ! grep -q "alias t=" "$SHELL_CONFIG"; then
    echo "alias t='$KIT_ROOT/bin/t'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias w=" "$SHELL_CONFIG"; then
    echo "alias w='$KIT_ROOT/bin/w'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias da=" "$SHELL_CONFIG"; then
    echo "alias da='$KIT_ROOT/bin/da'" >> "$SHELL_CONFIG"
fi

# Note: We added $KIT_ROOT to the path so python finds the file regardless of where you are
if ! grep -q "alias d=" "$SHELL_CONFIG"; then
    echo "alias d='python3 -m IPython --pdb $KIT_ROOT/custom/my_test.py'" >> "$SHELL_CONFIG"
fi

# 5. Also set them for the CURRENT session so they work right now
alias t="$KIT_ROOT/bin/t"
alias w="$KIT_ROOT/bin/w"
alias da="$KIT_ROOT/bin/da"
alias d="python3 -m IPython --pdb $KIT_ROOT/custom/my_test.py"

echo "Debug Kit Loaded!"
echo "Run 't' to test, 'w' to watch, 'da' to debug all."
echo "Aliases have been saved to $SHELL_CONFIG and will work in new terminals."