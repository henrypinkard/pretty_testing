# Darcula color palette (JetBrains-inspired) for PuDB — 16-color version
# This file is exec'd by PuDB with `palette`, `add_setting`, and `link` in scope.

link("current breakpoint", "current frame name")
link("focused current breakpoint", "focused current frame name")

palette.update({
    # base styles
    "background": ("white", "dark gray"),
    "selectable": ("white", "black"),
    "focused selectable": ("white", "dark gray"),
    "highlighted": ("white", "dark cyan"),
    "hotkey": (add_setting("brown", "underline"), "black"),
    # general ui
    "input": ("white", "black"),
    "button": (add_setting("white", "bold"), "dark gray"),
    "focused button": (add_setting("white", "bold"), "light gray"),
    "focused sidebar": ("brown", "dark gray"),
    "warning": (add_setting("white", "bold"), "dark red"),
    "group head": (add_setting("brown", "bold"), "black"),
    "dialog title": (add_setting("white", "bold"), "black"),
    # source view
    "source": ("light gray", "black"),
    "current source": (add_setting("white", "bold"), "dark gray"),
    "breakpoint source": (add_setting("white", "bold"), "dark red"),
    "line number": ("dark gray", "black"),
    "current line marker": (add_setting("yellow", "bold"), "black"),
    "breakpoint marker": (add_setting("dark red", "bold"), "black"),
    # sidebar
    "sidebar two": ("dark cyan", "black"),
    "focused sidebar two": ("dark cyan", "dark gray"),
    "sidebar three": ("light magenta", "black"),
    "focused sidebar three": ("light magenta", "dark gray"),
    # variables view
    "highlighted var label": ("white", "dark cyan"),
    "return label": ("light green", "black"),
    "focused return label": ("light green", "dark gray"),
    # stack
    "current frame name": ("light green", "black"),
    "focused current frame name": ("light green", "dark gray"),
    # shell
    "command line prompt": (add_setting("brown", "bold"), "black"),
    "command line output": ("light gray", "black"),
    "command line error": ("light red", "black"),
    "focused command line output": ("light gray", "dark gray"),
    "focused command line error": (add_setting("light red", "bold"), "dark gray"),
    # code syntax — Darcula-inspired mapping:
    # orange keywords → brown (closest 16-color)
    # green strings → dark green
    # blue literals → dark cyan
    # purple args → light magenta
    # yellow functions → yellow
    "literal":   ("dark cyan", "black"),
    "builtin":   ("brown", "black"),
    "exception": ("light red", "black"),
    "keyword2":  ("brown", "black"),
    "function":  ("yellow", "black"),
    "class":     (add_setting("yellow", "underline"), "black"),
    "keyword":   ("brown", "black"),
    "operator":  ("light gray", "black"),
    "comment":   ("dark gray", "black"),
    "docstring": ("dark green", "black"),
    "argument":  ("light magenta", "black"),
    "pseudo":    ("light magenta", "black"),
    "string":    ("dark green", "black"),
})
