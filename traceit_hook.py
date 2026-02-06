"""Auto-inject traceit_ into builtins so it works without imports."""
import builtins
from traceit_ import traceit_
builtins.traceit_ = traceit_
