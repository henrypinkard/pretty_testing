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


def _trace_line(debugger, abs_path=None, bp_target=None):
    """Return the set_trace injection string (no indent, no newline)."""
    if debugger == 'pdbpp':
        sticky = "hasattr(pdb,'DefaultConfig') and setattr(pdb.DefaultConfig,'sticky_by_default',True); "
        if bp_target and abs_path:
            return f'import pdb; {sticky}_dbg = pdb.Pdb(); _dbg.set_break("{abs_path}", {bp_target}); pdb.set_trace()'
        return f'import pdb; {sticky}pdb.set_trace()'
    else:
        if bp_target and abs_path:
            return f'import pudb; _dbg = pudb._get_debugger(); _dbg.set_break("{abs_path}", {bp_target}); pudb.set_trace()'
        return 'import pudb; pudb.set_trace()'


def inject_set_trace(lines, method, fail_line=0, abs_path=None, debugger='pudb'):
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

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method:
            body_line = node.body[0].lineno - 1
            indent = len(cleaned[body_line]) - len(cleaned[body_line].lstrip())
            pad = ' ' * indent
            bp_target = adj_fail + 1 if adj_fail > 0 else None
            trace = _trace_line(debugger, abs_path, bp_target)
            cleaned.insert(body_line, pad + trace + '\n')
            return cleaned

    # Fallback: method not found, inject at top
    trace = _trace_line(debugger)
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


def inject_setup_trace(lines, debugger='pudb'):
    """Inject set_trace into setUp body (or top of file if no setUp)."""
    source = ''.join(lines)
    tree = ast.parse(source)
    result = list(lines)

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'setUp':
            body_line = node.body[0].lineno - 1
            indent = len(result[body_line]) - len(result[body_line].lstrip())
            pad = ' ' * indent
            trace = _trace_line(debugger)
            result.insert(body_line, pad + trace + '\n')
            return result

    # No setUp found — inject at top
    trace = _trace_line(debugger)
    result.insert(0, trace + '\n')
    return result


def run_preflight(file_path, method):
    """Try importing the test file and running setUp. Returns (ok, error_msg)."""
    import importlib.util
    import unittest

    sys.path.insert(0, os.path.dirname(os.path.abspath(file_path)))
    spec = importlib.util.spec_from_file_location('_preflight_mod', file_path)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        return False, f'Import error: {e}'

    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and issubclass(obj, unittest.TestCase) and obj is not unittest.TestCase:
            try:
                instance = obj(method)
                instance.setUp()
            except Exception as e:
                return False, f'setUp failed: {e}'
            break

    return True, ''


def full_debug_prep(file_path, method, fail_line=0, debugger='pudb'):
    """All-in-one: prep the file, preflight, fall back to setUp injection if needed.

    This is the single entry point for both `w` and manual use.
    """
    with open(file_path) as f:
        original_lines = f.readlines()
    abs_path = os.path.abspath(file_path)
    result = inject_set_trace(original_lines, method, fail_line, abs_path, debugger)
    result = patch_postmortem(result, debugger)
    with open(file_path, 'w') as f:
        f.writelines(result)

    ok, err = run_preflight(file_path, method)
    if not ok:
        # setUp or import failed — start fresh from original, inject into setUp instead
        cleaned = remove_timeouts(original_lines)
        cleaned = neutralize_alarms(cleaned)
        result = inject_setup_trace(cleaned, debugger)
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
        full_debug_prep(args.file, args.method, args.fail_line, args.debugger)

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
