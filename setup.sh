#!/bin/bash

# 1. Get the absolute path to the folder where this script lives
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Install dependencies
pip3 install pudb pdbpp pygments > /dev/null 2>&1 || pip install pudb pdbpp pygments > /dev/null 2>&1

# 3a. Configure pdb++ (sticky mode by default)
PDBRC="$HOME/.pdbrc.py"
if [ ! -f "$PDBRC" ] || ! grep -q "sticky_by_default" "$PDBRC"; then
    cat >> "$PDBRC" << 'PDBCFG'
import pdb
class Config(pdb.DefaultConfig):
    sticky_by_default = True
PDBCFG
fi

# 3. Configure PuDB (custom Darcula theme, skip welcome screen)
PUDB_CONFIG_DIR="$HOME/.config/pudb"
mkdir -p "$PUDB_CONFIG_DIR"
if [ ! -f "$PUDB_CONFIG_DIR/pudb.cfg" ]; then
    cat > "$PUDB_CONFIG_DIR/pudb.cfg" << PUDBCFG
[pudb]
breakpoints_weight = 1
current_stack_frame = bottom
custom_shell =
custom_stringifier =
custom_theme =
default_variables_access_level = public
display = auto
hide_cmdline_win = False
hotkeys_breakpoints = B
hotkeys_code = C
hotkeys_stack = S
hotkeys_toggle_cmdline_focus = ctrl x
hotkeys_variables = V
line_numbers = True
prompt_on_quit = True
seen_welcome = e056
shell = internal
sidebar_width = 0.5
stack_weight = 1
stringifier = default
theme = $KIT_ROOT/darcula.py
variables_weight = 1
wrap_variables = True
PUDBCFG
fi

# 4. Make binaries executable
chmod +x "$KIT_ROOT/w"
chmod +x "$KIT_ROOT/help"
chmod +x "$KIT_ROOT/dbg"

# 5. Detect which shell config file to use (Zsh vs Bash)
if [ -f "$HOME/.zshrc" ]; then
    SHELL_CONFIG="$HOME/.zshrc"
else
    SHELL_CONFIG="$HOME/.bashrc"
fi

# 6. Append aliases to the config file so they persist after restart
# We check grep first to ensure we don't add the same alias multiple times
echo "Configuring aliases in $SHELL_CONFIG..."

export TERM=xterm-256color
if ! grep -q "TERM=xterm-256color" "$SHELL_CONFIG"; then
    echo "export TERM=xterm-256color" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias t=" "$SHELL_CONFIG"; then
    echo "alias t='$KIT_ROOT/t'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias w=" "$SHELL_CONFIG"; then
    echo "alias w='$KIT_ROOT/w'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias da=" "$SHELL_CONFIG"; then
    echo "alias da='$KIT_ROOT/da'" >> "$SHELL_CONFIG"
fi

# Note: We added $KIT_ROOT to the path so python finds the file regardless of where you are
if ! grep -q "alias d=" "$SHELL_CONFIG"; then
    echo "alias d='python3 -m IPython --pdb $KIT_ROOT/custom/my_test.py'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias h=" "$SHELL_CONFIG"; then
    echo "alias h='$KIT_ROOT/help'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias dbg=" "$SHELL_CONFIG"; then
    echo "alias dbg='$KIT_ROOT/dbg'" >> "$SHELL_CONFIG"
fi

# 7. Also set them for the CURRENT session so they work right now
alias t="$KIT_ROOT/t"
alias w="$KIT_ROOT/w"
alias da="$KIT_ROOT/da"
alias d="python3 -m IPython --pdb $KIT_ROOT/custom/my_test.py"
alias h="$KIT_ROOT/help"
alias dbg="$KIT_ROOT/dbg"

echo "Debug Kit Loaded!"
echo "Run 'w' to watch"
echo "Aliases have been saved to $SHELL_CONFIG and will work in new terminals."