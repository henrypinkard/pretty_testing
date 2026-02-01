# Darcula color palette (JetBrains-inspired) for PuDB — 16-color version
# This file is exec'd by PuDB with `palette`, `add_setting`, and `link` in scope.

link("current breakpoint", "current frame name")
link("focused current breakpoint", "focused current frame name")

palette.update({
    # base styles
    "background": ("white", "dark gray"),
    "selectable": ("white", "dark gray"),
    "focused selectable": ("white", "dark gray"),
    "highlighted": ("white", "dark cyan"),
    "hotkey": (add_setting("brown", "underline"), "dark gray"),
    # general ui
    "input": ("white", "dark gray"),
    "button": (add_setting("white", "bold"), "dark gray"),
    "focused button": (add_setting("white", "bold"), "light gray"),
    "focused sidebar": ("brown", "dark gray"),
    "warning": (add_setting("white", "bold"), "dark red"),
    "group head": (add_setting("brown", "bold"), "dark gray"),
    "dialog title": (add_setting("white", "bold"), "dark gray"),
    # source view
    "source": ("light gray", "dark gray"),
    "current source": (add_setting("white", "bold"), "dark gray"),
    "breakpoint source": (add_setting("white", "bold"), "dark red"),
    "line number": ("dark gray", "dark gray"),
    "current line marker": (add_setting("yellow", "bold"), "dark gray"),
    "breakpoint marker": (add_setting("dark red", "bold"), "dark gray"),
    # sidebar
    "sidebar two": ("dark cyan", "dark gray"),
    "focused sidebar two": ("dark cyan", "dark gray"),
    "sidebar three": ("light magenta", "dark gray"),
    "focused sidebar three": ("light magenta", "dark gray"),
    # variables view
    "highlighted var label": ("white", "dark cyan"),
    "return label": ("light green", "dark gray"),
    "focused return label": ("light green", "dark gray"),
    # stack
    "current frame name": ("light green", "dark gray"),
    "focused current frame name": ("light green", "dark gray"),
    # shell
    "command line prompt": (add_setting("brown", "bold"), "dark gray"),
    "command line output": ("light gray", "dark gray"),
    "command line error": ("light red", "dark gray"),
    "focused command line output": ("light gray", "dark gray"),
    "focused command line error": (add_setting("light red", "bold"), "dark gray"),
    # code syntax — Darcula-inspired mapping:
    # orange keywords → brown (closest 16-color)
    # green strings → dark green
    # blue literals → dark cyan
    # purple args → light magenta
    # yellow functions → yellow
    "literal":   ("dark cyan", "dark gray"),
    "builtin":   ("brown", "dark gray"),
    "exception": ("light red", "dark gray"),
    "keyword2":  ("brown", "dark gray"),
    "function":  ("yellow", "dark gray"),
    "class":     (add_setting("yellow", "underline"), "dark gray"),
    "keyword":   ("brown", "dark gray"),
    "operator":  ("light gray", "dark gray"),
    "comment":   ("dark gray", "dark gray"),
    "docstring": ("dark green", "dark gray"),
    "argument":  ("light magenta", "dark gray"),
    "pseudo":    ("light magenta", "dark gray"),
    "string":    ("dark green", "dark gray"),
})
