#!/usr/bin/env python3
"""
Debug file preparation: remove timeouts, neutralize alarms, inject debugger traces.

CLI:
    python3 debug_prep.py prep FILE --method NAME [--fail-line N] [--debugger pudb|pdbpp]
    python3 debug_prep.py preflight FILE --method NAME
    python3 debug_prep.py prep-setup FILE [--debugger pudb|pdbpp]
"""
import re
import ast
import os
import sys
import argparse


def remove_timeouts(lines):
    """Remove all @timeout decorator lines (with or without arguments)."""
    return [l for l in lines if not re.match(r'\s*@timeout\b', l)]


def neutralize_alarms(lines):
    """Replace signal.alarm(anything) with signal.alarm(0)."""
    return [re.sub(r'signal\.alarm\([^)]*\)', 'signal.alarm(0)', l) for l in lines]


MANUAL_BP_FILE = '_pretty_testing_/.manual_breakpoints'


def read_manual_breakpoints():
    """Read manual breakpoints from file. Returns list of (filepath, line) tuples."""
    if not os.path.exists(MANUAL_BP_FILE):
        return []
    breakpoints = []
    with open(MANUAL_BP_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Format: filepath:line
            if ':' in line:
                parts = line.rsplit(':', 1)
                if len(parts) == 2:
                    filepath, lineno = parts
                    try:
                        breakpoints.append((filepath, int(lineno)))
                    except ValueError:
                        pass
    return breakpoints


def _error_summary_print():
    """Return code that prints the error summary file if it exists."""
    return "import os as _os; _es='_pretty_testing_/.error_summary'; _os.path.exists(_es) and print(open(_es).read())"


def _trace_line(debugger, abs_path=None, bp_target=None, user_error_file=None, user_error_line=None,
                manual_breakpoints=None):
    """Return the set_trace injection string (no indent, no newline)."""
    manual_breakpoints = manual_breakpoints or []
    if debugger == 'pdbpp':
        sticky = "hasattr(pdb,'DefaultConfig') and setattr(pdb.DefaultConfig,'sticky_by_default',True); "
        parts = [f'import pdb; {sticky}_dbg = pdb.Pdb()']
        if bp_target and abs_path:
            parts.append(f'_dbg.set_break("{abs_path}", {bp_target})')
        if user_error_file and user_error_line:
            parts.append(f'_dbg.set_break("{user_error_file}", {user_error_line})')
        # Add manual breakpoints
        for bp_file, bp_line in manual_breakpoints:
            parts.append(f'_dbg.set_break("{bp_file}", {bp_line})')
        parts.append(_error_summary_print())
        parts.append('pdb.set_trace()')
        return '; '.join(parts)
    else:
        parts = ['import pudb; _dbg = pudb._get_debugger()']
        if bp_target and abs_path:
            parts.append(f'_dbg.set_break("{abs_path}", {bp_target})')
        if user_error_file and user_error_line:
            parts.append(f'_dbg.set_break("{user_error_file}", {user_error_line})')
        # Add manual breakpoints
        for bp_file, bp_line in manual_breakpoints:
            parts.append(f'_dbg.set_break("{bp_file}", {bp_line})')
        parts.append(_error_summary_print())
        parts.append('pudb.set_trace()')
        return '; '.join(parts)


def _trace_line_multi(debugger, abs_path=None, bp_targets=None, user_error_file=None, user_error_line=None,
                      manual_breakpoints=None):
    """Return set_trace injection with multiple breakpoints (no indent, no newline)."""
    bp_targets = bp_targets or []
    manual_breakpoints = manual_breakpoints or []
    if debugger == 'pdbpp':
        sticky = "hasattr(pdb,'DefaultConfig') and setattr(pdb.DefaultConfig,'sticky_by_default',True); "
        parts = [f'import pdb; {sticky}_dbg = pdb.Pdb()']
        for bp in bp_targets:
            if abs_path:
                parts.append(f'_dbg.set_break("{abs_path}", {bp})')
        if user_error_file and user_error_line:
            parts.append(f'_dbg.set_break("{user_error_file}", {user_error_line})')
        # Add manual breakpoints
        for bp_file, bp_line in manual_breakpoints:
            parts.append(f'_dbg.set_break("{bp_file}", {bp_line})')
        parts.append(_error_summary_print())
        parts.append('pdb.set_trace()')
        return '; '.join(parts)
    else:
        parts = ['import pudb; _dbg = pudb._get_debugger()']
        for bp in bp_targets:
            if abs_path:
                parts.append(f'_dbg.set_break("{abs_path}", {bp})')
        if user_error_file and user_error_line:
            parts.append(f'_dbg.set_break("{user_error_file}", {user_error_line})')
        # Add manual breakpoints
        for bp_file, bp_line in manual_breakpoints:
            parts.append(f'_dbg.set_break("{bp_file}", {bp_line})')
        parts.append(_error_summary_print())
        parts.append('pudb.set_trace()')
        return '; '.join(parts)


def inject_set_trace(lines, method, fail_line=0, abs_path=None, debugger='pudb',
                     user_error_file=None, user_error_line=None):
    """Inject set_trace (and optionally set_break) at the start of the given method body.

    Returns modified lines list.
    """
    # Count @timeout lines before fail_line that will be removed
    removed = sum(1 for i, l in enumerate(lines[:max(0, fail_line - 1)])
                  if re.match(r'\s*@timeout\b', l))
    adj_fail = fail_line - removed if fail_line > 0 else 0

    cleaned = remove_timeouts(lines)
    cleaned = neutralize_alarms(cleaned)

    source = ''.join(cleaned)
    tree = ast.parse(source)

    # Read manual breakpoints
    manual_bps = read_manual_breakpoints()

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method:
            body_line = node.body[0].lineno - 1
            indent = len(cleaned[body_line]) - len(cleaned[body_line].lstrip())
            pad = ' ' * indent
            bp_target = adj_fail + 1 if adj_fail > 0 else None
            trace = _trace_line(debugger, abs_path, bp_target, user_error_file, user_error_line,
                               manual_breakpoints=manual_bps)
            cleaned.insert(body_line, pad + trace + '\n')
            return cleaned

    # Fallback: method not found, inject at top
    trace = _trace_line(debugger, user_error_file=user_error_file, user_error_line=user_error_line,
                       manual_breakpoints=manual_bps)
    cleaned.insert(0, trace + '\n')
    return cleaned


def patch_postmortem(lines, debugger):
    """Replace 'raise e' in runner block with filtered post_mortem.

    Walks the traceback to the last frame in the user's test file, truncates
    tb_next so the debugger can't descend into unittest internals, then calls
    post_mortem at the correct frame.
    Uses e.__traceback__ directly (e is in scope from the except block).
    """
    pm_mod = 'pudb' if debugger == 'pudb' else 'pdb'
    # Indentation matches the runner block in test_generator.py (16 spaces)
    pad = ' ' * 16
    replacement = (
        f"{pad}import sys as _s; _tb = _s.exc_info()[2]; _ut = _tb\n"
        f"{pad}while _tb:\n"
        f"{pad}    if _tb.tb_frame.f_code.co_filename == __file__: _ut = _tb\n"
        f"{pad}    _tb = _tb.tb_next\n"
        f"{pad}try: _ut.tb_next = None\n"
        f"{pad}except: pass\n"
        f"{pad}import {pm_mod}; {pm_mod}.post_mortem()\n"
    )
    result = []
    patched = False
    for line in lines:
        if not patched and line.strip() == 'raise e':
            result.append(replacement)
            patched = True
        else:
            result.append(line)
    return result


def inject_setup_trace(lines, debugger='pudb', method=None, fail_line=0, abs_path=None,
                       user_error_file=None, user_error_line=None):
    """Inject set_trace into setUp body (or top of file if no setUp).

    When method/fail_line/abs_path are provided, also sets breakpoints at:
    - The first line of the target method body
    - The fail line (adjusted for the injection offset)
    """
    source = ''.join(lines)
    tree = ast.parse(source)
    result = list(lines)

    # Read manual breakpoints
    manual_bps = read_manual_breakpoints()

    # Find the target method's body start line (before any injection)
    method_body_line = None
    if method:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == method:
                method_body_line = node.body[0].lineno
                break

    # Find setUp and inject set_trace
    setup_found = False
    setup_injection_line = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'setUp':
            body_line = node.body[0].lineno - 1
            setup_injection_line = body_line
            indent = len(result[body_line]) - len(result[body_line].lstrip())
            pad = ' ' * indent

            # Calculate breakpoints (they'll be offset by 1 after injection)
            bp_targets = []
            if method_body_line and abs_path:
                # Breakpoint at method body start (will be +1 after injection)
                bp_targets.append(method_body_line + 1)
            if fail_line and abs_path and fail_line != method_body_line:
                # Breakpoint at fail line (also +1 after injection)
                bp_targets.append(fail_line + 1)

            trace = _trace_line_multi(debugger, abs_path, bp_targets, user_error_file, user_error_line,
                                      manual_breakpoints=manual_bps)
            result.insert(body_line, pad + trace + '\n')
            setup_found = True
            break

    if not setup_found:
        # No setUp found — inject at top
        bp_targets = []
        if method_body_line and abs_path:
            bp_targets.append(method_body_line + 1)
        if fail_line and abs_path and fail_line != method_body_line:
            bp_targets.append(fail_line + 1)
        trace = _trace_line_multi(debugger, abs_path, bp_targets, user_error_file, user_error_line,
                                  manual_breakpoints=manual_bps)
        result.insert(0, trace + '\n')

    return result


def run_preflight(file_path, method):
    """Try importing the test file and running setUp. Returns (ok, error_msg).

    Finds the TestCase class that contains the target method (handles multiple classes).
    """
    import importlib.util
    import unittest

    sys.path.insert(0, os.path.dirname(os.path.abspath(file_path)))
    spec = importlib.util.spec_from_file_location('_preflight_mod', file_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return False, f'Import error: {e}'

    # Find the class that contains the target method
    target_class = None
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
            if hasattr(obj, method):
                target_class = obj
                break

    if target_class is None:
        return False, f'No TestCase class contains method {method}'

    try:
        instance = target_class(method)
        # Only call setUp if the class has one (not setUpClass)
        if hasattr(instance, 'setUp') and callable(getattr(instance, 'setUp')):
            instance.setUp()
    except Exception as e:
        return False, f'setUp failed: {e}'

    return True, ''


def full_debug_prep(file_path, method, fail_line=0, debugger='pudb',
                    user_error_file=None, user_error_line=None):
    """All-in-one: prep the file, preflight, fall back to setUp injection if needed.

    This is the single entry point for both `w` and manual use.
    """
    with open(file_path) as f:
        original_lines = f.readlines()
    abs_path = os.path.abspath(file_path)
    result = inject_set_trace(original_lines, method, fail_line, abs_path, debugger,
                              user_error_file, user_error_line)
    result = patch_postmortem(result, debugger)
    with open(file_path, 'w') as f:
        f.writelines(result)

    ok, err = run_preflight(file_path, method)
    if not ok:
        # setUp or import failed — start fresh from original, inject into setUp instead
        cleaned = remove_timeouts(original_lines)
        cleaned = neutralize_alarms(cleaned)
        # Pass breakpoint info so we stop at the right place after setUp
        result = inject_setup_trace(cleaned, debugger, method=method, fail_line=fail_line,
                                    abs_path=abs_path, user_error_file=user_error_file,
                                    user_error_line=user_error_line)
        result = patch_postmortem(result, debugger)
        with open(file_path, 'w') as f:
            f.writelines(result)
        print(f'preflight failed ({err}), injected trace into setUp', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command')

    # All-in-one command
    p_debug = sub.add_parser('debug', help='Full prep+preflight+fallback in one step')
    p_debug.add_argument('file')
    p_debug.add_argument('--method', required=True)
    p_debug.add_argument('--fail-line', type=int, default=0)
    p_debug.add_argument('--debugger', choices=['pudb', 'pdbpp'], default='pudb')
    p_debug.add_argument('--user-error-file', default=None, help='File where user code error originated')
    p_debug.add_argument('--user-error-line', type=int, default=0, help='Line in user code where error originated')

    # Individual commands (still available for testing / granular use)
    p_prep = sub.add_parser('prep')
    p_prep.add_argument('file')
    p_prep.add_argument('--method', required=True)
    p_prep.add_argument('--fail-line', type=int, default=0)
    p_prep.add_argument('--debugger', choices=['pudb', 'pdbpp'], default='pudb')

    p_pre = sub.add_parser('preflight')
    p_pre.add_argument('file')
    p_pre.add_argument('--method', required=True)

    p_setup = sub.add_parser('prep-setup')
    p_setup.add_argument('file')
    p_setup.add_argument('--debugger', choices=['pudb', 'pdbpp'], default='pudb')

    args = parser.parse_args()

    if args.command == 'debug':
        user_file = args.user_error_file if args.user_error_file else None
        user_line = args.user_error_line if args.user_error_line else None
        full_debug_prep(args.file, args.method, args.fail_line, args.debugger,
                        user_file, user_line)

    elif args.command == 'prep':
        with open(args.file) as f:
            lines = f.readlines()
        abs_path = os.path.abspath(args.file)
        result = inject_set_trace(lines, args.method, args.fail_line, abs_path, args.debugger)
        with open(args.file, 'w') as f:
            f.writelines(result)

    elif args.command == 'preflight':
        ok, err = run_preflight(args.file, args.method)
        if not ok:
            print(err, file=sys.stderr)
            sys.exit(1)

    elif args.command == 'prep-setup':
        with open(args.file) as f:
            lines = f.readlines()
        result = inject_setup_trace(lines, args.debugger)
        with open(args.file, 'w') as f:
            f.writelines(result)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
