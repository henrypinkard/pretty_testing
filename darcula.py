# Darcula color palette (JetBrains-inspired) for PuDB — 256-color version
# This file is exec'd by PuDB with `palette`, `add_setting`, and `link` in scope.

bg = "h235"           # #2B2B2B
bg_lighter = "h237"   # #3C3F41
bg_selected = "h239"  # #4E5254
dark_red = "h124"
green = "h114"        # #6A8759
bright_green = "h150" # #A5C261
yellow = "h180"       # #D4A656
orange = "h173"       # #CC7832
blue = "h68"          # #6897BB
purple = "h176"       # #9876AA
white = "h253"        # #A9B7C6
gray = "h245"         # #808080
red = "h167"          # #D25252
bright_white = "h255"
teal = "h30"

link("current breakpoint", "current frame name")
link("focused current breakpoint", "focused current frame name")

palette.update({
    # base styles
    "background": ("h250", "h236"),
    "selectable": (white, bg),
    "focused selectable": (bright_white, bg_selected),
    "highlighted": (bright_white, teal),
    "hotkey": (add_setting(orange, "underline"), "h236"),
    # general ui
    "input": (white, bg),
    "button": (add_setting(white, "bold"), bg_lighter),
    "focused button": (add_setting(bright_white, "bold"), bg_selected),
    "focused sidebar": (orange, bg_lighter),
    "warning": (add_setting(bright_white, "bold"), dark_red),
    "group head": (add_setting(orange, "bold"), "h236"),
    "dialog title": (add_setting(bright_white, "bold"), bg),
    # source view
    "source": (white, bg),
    "current source": (add_setting(bright_white, "bold"), bg_selected),
    "breakpoint source": (add_setting(bright_white, "bold"), dark_red),
    "line number": (gray, bg),
    "current line marker": (add_setting(yellow, "bold"), bg),
    "breakpoint marker": (add_setting(red, "bold"), bg),
    # sidebar
    "sidebar two": (blue, bg),
    "focused sidebar two": (blue, bg_selected),
    "sidebar three": (purple, bg),
    "focused sidebar three": (purple, bg_selected),
    # variables view
    "highlighted var label": (bright_white, teal),
    "return label": (bright_green, bg),
    "focused return label": (bright_green, bg_selected),
    # stack
    "current frame name": (bright_green, bg),
    "focused current frame name": (bright_green, bg_selected),
    # shell
    "command line prompt": (add_setting(orange, "bold"), bg),
    "command line output": (white, bg),
    "command line error": (red, bg),
    "focused command line output": (white, bg_selected),
    "focused command line error": (add_setting(red, "bold"), bg_selected),
    # code syntax
    "literal":   (blue, bg),
    "builtin":   (orange, bg),
    "exception": (red, bg),
    "keyword2":  (orange, bg),
    "function":  (yellow, bg),
    "class":     (add_setting(yellow, "underline"), bg),
    "keyword":   (orange, bg),
    "operator":  (white, bg),
    "comment":   (gray, bg),
    "docstring": (green, bg),
    "argument":  (purple, bg),
    "pseudo":    (purple, bg),
    "string":    (green, bg),
})
