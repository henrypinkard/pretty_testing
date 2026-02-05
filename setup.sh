#!/bin/bash

# 1. Get the absolute path to the folder where this script lives
KIT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 2. Install dependencies
# Only install if not already present (avoids slow PyPI check)
python3 -c "import pudb, pdbpp, pygments" 2>/dev/null || {
    echo "Installing dependencies..."
    pip3 install "pudb==2025.1.5" pdbpp pygments || \
    pip install "pudb==2025.1.5" pdbpp pygments
}

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
breakpoints_weight = 0.2
current_stack_frame = bottom
custom_shell =
custom_stringifier =
custom_theme =
default_variables_access_level = public
display = auto
cmdline_height = 3.0517578125
hide_cmdline_win = True
hotkeys_breakpoints = B
hotkeys_code = C
hotkeys_stack = S
hotkeys_toggle_cmdline_focus = ctrl x
hotkeys_variables = V
line_numbers = True
prompt_on_quit = True
seen_welcome = e056
shell = internal
sidebar_width = 0.34359738368000003
stack_weight = 0.32768
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
chmod +x "$KIT_ROOT/bp"
chmod +x "$KIT_ROOT/skip"
chmod +x "$KIT_ROOT/debug"
chmod +x "$KIT_ROOT/untrace"

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
    echo "alias d='python3 -m IPython --pdb $KIT_ROOT/_pretty_testing_/debug_this_test.py'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias h=" "$SHELL_CONFIG"; then
    echo "alias h='$KIT_ROOT/help'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias dbg=" "$SHELL_CONFIG"; then
    echo "alias dbg='$KIT_ROOT/dbg'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias bp=" "$SHELL_CONFIG"; then
    echo "alias bp='$KIT_ROOT/bp'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias skip=" "$SHELL_CONFIG"; then
    echo "alias skip='$KIT_ROOT/skip'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias debug=" "$SHELL_CONFIG"; then
    echo "alias debug='$KIT_ROOT/debug'" >> "$SHELL_CONFIG"
fi

if ! grep -q "alias untrace=" "$SHELL_CONFIG"; then
    echo "alias untrace='$KIT_ROOT/untrace'" >> "$SHELL_CONFIG"
fi

# 7. Also set them for the CURRENT session so they work right now
alias t="$KIT_ROOT/t"
alias w="$KIT_ROOT/w"
alias da="$KIT_ROOT/da"
alias d="python3 -m IPython --pdb $KIT_ROOT/_pretty_testing_/debug_this_test.py"
alias h="$KIT_ROOT/help"
alias dbg="$KIT_ROOT/dbg"
alias bp="$KIT_ROOT/bp"
alias skip="$KIT_ROOT/skip"
alias debug="$KIT_ROOT/debug"
alias untrace="$KIT_ROOT/untrace"

echo "Debug Kit Loaded!"
echo "Run 'w' to watch"
echo "Aliases have been saved to $SHELL_CONFIG and will work in new terminals."

# =============================================================================
# STATIC ANALYSIS TOOLS (optional - dependencies installed on first use)
# =============================================================================

# Create lint command
chmod +x "$KIT_ROOT/lint" 2>/dev/null || true

# Add alias
if ! grep -q "alias lint=" "$SHELL_CONFIG"; then
    echo "alias lint='$KIT_ROOT/lint'" >> "$SHELL_CONFIG"
fi

alias lint="$KIT_ROOT/lint"

echo ""
echo "Static analysis available. Run 'lint' to check code (dependencies installed on first use)."

# =============================================================================
# TRACE DECORATOR (copy to working directory)
# =============================================================================

TRACE_WARNING=""
TRACE_DEST="trace.py"

# Check for collision
if [ -f "$TRACE_DEST" ]; then
    # Same content? Skip copy entirely.
    if python3 -c "import hashlib,sys; h=lambda f:hashlib.md5(open(f,'rb').read()).hexdigest(); sys.exit(0 if h(sys.argv[1])==h(sys.argv[2]) else 1)" "$TRACE_DEST" "$KIT_ROOT/trace.py"; then
        echo ""
        echo "Trace decorator already up to date: $TRACE_DEST"
    else
        # Different file — find a unique name with underscores
        PREFIX="_"
        while [ -f "${PREFIX}trace.py" ]; do
            PREFIX="_${PREFIX}"
        done
        TRACE_DEST="${PREFIX}trace.py"
        TRACE_WARNING="trace.py"
        cp "$KIT_ROOT/trace.py" "$TRACE_DEST"
        echo ""
        echo "Trace decorator installed: $TRACE_DEST"
        echo "  Usage: from ${TRACE_DEST%.py} import trace"
    fi
else
    cp "$KIT_ROOT/trace.py" "$TRACE_DEST"
    echo ""
    echo "Trace decorator installed: $TRACE_DEST"
    echo "  Usage: from ${TRACE_DEST%.py} import trace"
fi

# Print warning at the very end if there was a collision
if [ -n "$TRACE_WARNING" ]; then
    echo ""
    echo -e "\033[31m⚠ WARNING: '$TRACE_WARNING' already exists in this directory.\033[0m"
    echo -e "\033[31m  Trace decorator was installed as '$TRACE_DEST' instead.\033[0m"
    echo -e "\033[31m  Use: from ${TRACE_DEST%.py} import trace\033[0m"
fi