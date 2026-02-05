"""
Recursive function tracing decorator for debugging.

Usage:
    @trace
    def my_recursive_func(n):
        ...

Options:
    max_depth=20     Max recursion depth to print
    show_returns=True   Show return values (└─>)
    max_len=50       Truncate long reprs
    indent="\t"      Indentation per level (tab by default)
    watch=[0,2]      Only show args at these positions (others: ·)
    show_depth=False Show [depth] prefix
    show_exc=True    Show exceptions at each level (False: only first)

Examples:
    @trace(max_depth=10, show_returns=False)
    def fibonacci(n): ...

    @trace(watch=[2, 3])  # Only show low, high
    def binary_search(arr, target, low, high): ...

    @trace(show_depth=True)  # See exact recursion depth
    def deep_recursion(n): ...
"""

import functools


def _smart_truncate(obj, max_len=40):
    """Truncate with smarter handling of common types."""
    if obj is None:
        return "None"

    # Class instances have ugly default reprs, so just show class name
    # (but not NamedTuples - they have nice reprs already)
    if (hasattr(obj, '__dict__') and not isinstance(obj, type)
            and not hasattr(obj, '_fields')):
        type_name = type(obj).__name__
        return f"<{type_name}>"

    s = repr(obj)
    if len(s) <= max_len:
        return s

    # For dicts, show first key-value pair if it has a 'value' key (common in trees)
    if isinstance(obj, dict):
        if 'value' in obj:
            v = repr(obj['value'])
            if len(v) > 15:
                v = v[:12] + "..."
            return f"{{{repr('value')}: {v}, ...}}"
        elif len(obj) > 0:
            first_key = next(iter(obj))
            first_val = repr(obj[first_key])
            if len(first_val) > 15:
                first_val = first_val[:12] + "..."
            return f"{{{repr(first_key)}: {first_val}, ...}}"
        return "{}"

    elif isinstance(obj, (list, tuple)):
        bracket = "[]" if isinstance(obj, list) else "()"
        if len(obj) == 0:
            return bracket
        # Show first element and count
        first = repr(obj[0])
        if len(first) > 15:
            first = first[:12] + "..."
        if len(obj) == 1:
            return f"{bracket[0]}{first}{bracket[1]}"
        return f"{bracket[0]}{first}, ...+{len(obj)-1}{bracket[1]}"

    elif isinstance(obj, set):
        if len(obj) == 0:
            return "set()"
        return f"{{...{len(obj)} items}}"

    elif isinstance(obj, str):
        if len(obj) > max_len - 5:
            return repr(obj[:max_len-8] + "...")
        return s

    else:
        return s[:max_len-3] + "..."


def _format_args(args, kwargs, max_len=40, watch=None):
    """
    Format function arguments for display.

    Args:
        args: Positional arguments
        kwargs: Keyword arguments
        max_len: Max length for each argument repr
        watch: If set, only show arguments at these positions (0-indexed)
    """
    parts = []
    start_idx = 0

    # Skip 'self' for bound methods - it's just noise
    if len(args) > 0:
        first = args[0]
        if hasattr(first, '__dict__') and not isinstance(first, type):
            start_idx = 1

    for i, a in enumerate(args):
        if i < start_idx:
            continue
        # Adjust index for watch when we've skipped self
        watch_idx = i - start_idx
        if watch is None or watch_idx in watch:
            parts.append(_smart_truncate(a, max_len))
        else:
            parts.append("·")

    for k, v in kwargs.items():
        parts.append(f"{k}={_smart_truncate(v, max_len)}")

    return ", ".join(parts)


def trace(_func=None, *, max_depth=20, show_returns=True, max_len=250, indent="\t",
          watch=None, show_depth=False, show_exc=True, limit=None):
    """
    Decorator to trace recursive function calls.

    Args:
        max_depth: Maximum recursion depth to print (default 20)
        show_returns: Whether to print return values (default True)
        max_len: Maximum length for argument/return value repr (default 50)
        indent: String to use for each indentation level (default "\t")
        watch: List of argument positions (0-indexed) to show in detail.
               Other args shown as "·". None means show all. (default None)
        show_depth: If True, prefix each line with [depth] (default False)
        show_exc: If True, show exceptions at each level. If False, only
                  at the level where it occurred. (default True)

    Examples:
        @trace
        def factorial(n): ...

        @trace(max_depth=5, show_returns=False)
        def fibonacci(n): ...

        @trace(watch=[2, 3])  # Only show low, high for binary search
        def binary_search(arr, target, low, high): ...

        @trace(show_depth=True)  # Show [0], [1], [2] prefix
        def deep_recursion(n): ...
    """
    def decorator(func):
        depth = [0]
        # Track if we've already shown an exception (to avoid repeats)
        exc_shown = [False]

        # Tree-drawing characters, sized to match indent
        pipe = "│" + indent      # vertical continuation
        tee  = "├──" + indent    # branch (call)
        ret  = "└─>" + indent    # return value
        exc  = "└─✕" + indent    # exception

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_depth = depth[0]
            d = current_depth
            dp = f"[{d}] " if show_depth else ""

            # Build prefixes for call, return, and exception lines
            if d == 0:
                call_pfx = dp
            else:
                call_pfx = dp + pipe * (d - 1) + tee
            ret_pfx = dp + pipe * d + ret
            exc_pfx = dp + pipe * d + exc

            if d < max_depth:
                args_str = _format_args(args, kwargs, max_len, watch)
                call_str = f"{func.__name__}({args_str})"
                if '\n' in call_str:
                    # Multi-line args (e.g. 2D numpy arrays):
                    # indent continuation lines to align under the opening paren
                    pad = call_pfx + " " * (len(func.__name__) + 1)
                    call_str = call_str.replace('\n', '\n' + pad)
                print(f"{call_pfx}{call_str}")
            elif d == max_depth:
                print(f"{call_pfx}... (max depth {max_depth} reached)")

            depth[0] += 1
            exc_shown[0] = False  # Reset for this call

            if limit is not None and d >= limit:
                depth[0] -= 1
                raise RecursionError(f"trace limit={limit} exceeded")

            try:
                result = func(*args, **kwargs)
            except Exception as e:
                depth[0] -= 1
                if d < max_depth:
                    if show_exc or not exc_shown[0]:
                        print(f"{exc_pfx}{type(e).__name__}: {str(e)[:60]}")
                        exc_shown[0] = True
                    else:
                        print(f"{dp + pipe * d}└─✕")
                raise

            depth[0] -= 1

            if show_returns and d < max_depth:
                result_str = _smart_truncate(result, max_len)
                print(f"{ret_pfx}{result_str}")

            return result

        wrapper._depth = depth
        wrapper._reset = lambda: depth.__setitem__(0, 0)
        return wrapper

    if _func is not None:
        return decorator(_func)
    return decorator


def reset_trace(traced_func):
    """Reset the depth counter for a traced function."""
    if hasattr(traced_func, '_reset'):
        traced_func._reset()


if __name__ == "__main__":
    print("=== Test 1: Simple factorial ===")

    @trace
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n - 1)

    factorial(5)

    print("\n=== Test 2: Binary search with watch ===")

    @trace(watch=[2, 3])  # Only show low, high
    def binary_search(arr, target, low, high):
        if low > high:
            return -1
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            return binary_search(arr, target, mid + 1, high)
        else:
            return binary_search(arr, target, low, mid - 1)

    binary_search([1,2,3,4,5,6,7,8,9,10], 7, 0, 9)

    print("\n=== Test 3: Tree with value display ===")

    @trace
    def tree_sum(node):
        if node is None:
            return 0
        return node['value'] + tree_sum(node.get('left')) + tree_sum(node.get('right'))

    tree = {
        'value': 10,
        'left': {'value': 5, 'left': None, 'right': None},
        'right': {'value': 15, 'left': None, 'right': None}
    }
    tree_sum(tree)
