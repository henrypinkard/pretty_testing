"""Auto-inject _rtrace into builtins so it works without imports."""
import builtins
from _rtrace import _rtrace
builtins._rtrace = _rtrace
