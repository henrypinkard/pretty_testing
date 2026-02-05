#!/usr/bin/env python3
"""
Test output colorization — extracted from inline Python in `w`.

CLI:
    python3 output_parser.py crash       # stdin: raw crash output → colorized
    python3 output_parser.py source FILE METHOD FAIL_LINE
    python3 output_parser.py trace       # stdin: raw trace → parsed sections
    python3 output_parser.py error       # stdin: error summary → colorized
    python3 output_parser.py syntax      # stdin: syntax error → pygments colored
"""
import sys
import re
import os

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer, PythonTracebackLexer
    from pygments.formatters import TerminalFormatter
    has_pygments = True
except ImportError:
    has_pygments = False


def colorize_crash(text):
    """Colorize a crash traceback, showing only from the last frame."""
    lines = text.splitlines()
    last_frame_start = -1
    for i, line in enumerate(lines):
        if line.strip().startswith('File "'):
            last_frame_start = i
    crash_lines = lines[last_frame_start:] if last_frame_start != -1 else lines
    out = []
    for line in crash_lines:
        match = re.search(r'(File ")(.*?)(", line )(\d+)(, in )(.*)', line)
        if match:
            prefix, path, mid1, lineno, mid2, method = match.groups()
            out.append(f'  {prefix}\033[34m{path}\033[0m{mid1}\033[32m{lineno}\033[0m{mid2}\033[33m{method}\033[0m')
            continue
        if 'Error:' in line or 'Exception:' in line:
            out.append(f'\033[31m{line}\033[0m')
            continue
        if '    ' in line:
            out.append(f'\033[1m{line}\033[0m')
            continue
        out.append(line)
    return '\n'.join(out)


def extract_source(file_path, target_name, fail_line_abs, orig_file=None):
    """Extract source code up to the failing line with syntax highlighting."""
    import ast
    os.environ['TERM'] = 'xterm-256color'

    try:
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source)
        method_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == target_name:
                method_node = node
                break

        if method_node:
            rel_fail_idx = fail_line_abs - method_node.lineno
            end = fail_line_abs if fail_line_abs > 0 else method_node.end_lineno
            lines = source.splitlines()[method_node.lineno - 1: end]
            if lines:
                indent_size = len(lines[0]) - len(lines[0].lstrip())
                lines = [line[indent_size:] for line in lines]
            code_str = '\n'.join(lines)
            if has_pygments:
                formatted = highlight(code_str, PythonLexer(), TerminalFormatter())
            else:
                formatted = code_str
            out_lines = formatted.splitlines()
            final_lines = []
            for i, line in enumerate(out_lines):
                if i == rel_fail_idx and fail_line_abs > 0:
                    line = f'\x1b[91m--> \x1b[0m{line}'
                else:
                    line = f'    {line}'
                final_lines.append(line)
            return '\n'.join(final_lines)
        else:
            return 'Method source not found.'
    except Exception as e:
        return f'Error extracting source: {e}'


def parse_trace(text):
    """Parse raw trace into sections. Returns (error_msg, exec_log) separated by ___SECTION_SEP___."""
    def colorize_code(code_str):
        if has_pygments:
            try:
                return highlight(code_str, PythonLexer(), TerminalFormatter()).rstrip()
            except Exception:
                pass
        code_str = re.sub(r'(".*?"|\'.*?\')', r'\033[32m\1\033[0m', code_str)
        code_str = re.sub(r'\b(\d+)\b', r'\033[36m\1\033[0m', code_str)
        keywords = r'\b(def|class|return|if|else|elif|while|for|in|try|except|import|from|as|pass|None|True|False)\b'
        code_str = re.sub(keywords, r'\033[33m\1\033[0m', code_str)
        code_str = re.sub(r'\b(self)\b', r'\033[35m\1\033[0m', code_str)
        return code_str

    state = 0
    buf_log = []
    failure_summary = []

    for line in text.splitlines(True):
        clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
        if '___TEST_START___' in clean:
            state = 1
            continue
        if '___FAILURE_SUMMARY_START___' in clean:
            state = 5
            continue
        if '___FAILURE_SUMMARY_END___' in clean:
            state = 1
            continue

        if state == 5:
            failure_summary.append(line.rstrip())  # preserve leading whitespace (indentation)
            continue
        if state == 1:
            if clean.startswith('[EXE] '):
                code = clean.replace('[EXE] ', '')
                colored_code = colorize_code(code)
                buf_log.append(f'  \033[1;34m>>\033[0m {colored_code}\n')
            elif 'Traceback (most recent call last)' in clean:
                state = 3
            else:
                buf_log.append(f'  \033[2m{line}\033[0m')
        elif state == 3:
            pass

    out = '___SECTION_SEP___\n'
    out += '\n'.join(failure_summary)
    out += '\n___SECTION_SEP___\n'
    out += ''.join(buf_log)
    return out


def colorize_error(text):
    """Colorize error summary lines."""
    out = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.endswith(':') and ('Error' in line or 'Exception' in line):
            out.append(f'  \033[1;31m{line}\033[0m')
            continue
        m2 = re.match(r'(\s*Actual:\s*)(.*)', line)
        if m2:
            out.append(f'  \033[1mActual:   \033[33m{m2.group(2)}\033[0m')
            continue
        m3 = re.match(r'(\s*Expected:\s*)(.*)', line)
        if m3:
            out.append(f'  \033[1mExpected: \033[32m{m3.group(2)}\033[0m')
            continue
        m4 = re.match(r'(\w+(?:Error|Exception|Interrupt|Iteration|Exit)):\s*(.*)', line)
        if m4:
            out.append(f'  \033[1;31m{m4.group(1)}:\033[0m {m4.group(2)}')
            continue
        out.append(f'  {line}')
    return '\n'.join(out)


def colorize_syntax(text):
    """Colorize syntax error output using pygments."""
    if has_pygments:
        return highlight(text, PythonTracebackLexer(), TerminalFormatter()).rstrip()
    return text


def _is_stdlib_or_thirdparty(path):
    """Check if a path is stdlib or third-party (site-packages)."""
    if path.startswith('<'):  # <string>, <frozen>, etc.
        return True
    if '/lib/python' in path or '\\lib\\python' in path:
        return True
    if 'site-packages' in path or 'dist-packages' in path:
        return True
    return False


def extract_relevant_traceback(text, test_file):
    """Extract relevant frames from traceback: test file + user code, excluding stdlib.

    Returns a list of (file_path, line_number, method_name) tuples representing
    the relevant portion of the stack trace.

    The logic:
    1. Include frames from the test file (but NOT <module> runner frames)
    2. Include frames from user code (not stdlib, not site-packages)
    3. Stop once we encounter stdlib/third-party code (don't include those frames)

    This way:
    - If assertion fails in test: returns just the test frame
    - If user code raises: returns test frame + chain of user code frames
    - If user code calls stdlib and stdlib raises: returns test + user code, NOT stdlib
    """
    # Parse traceback frames: File "path", line N, in method
    frame_pattern = re.compile(
        r'File "([^"]+)", line (\d+), in (.+?)$',
        re.MULTILINE
    )

    all_frames = []
    for match in frame_pattern.finditer(text):
        file_path, lineno, method = match.groups()
        all_frames.append((file_path, int(lineno), method.strip()))

    if not all_frames:
        return []

    test_basename = os.path.basename(test_file) if test_file else None
    relevant_frames = []

    for frame in all_frames:
        file_path, lineno, method = frame
        file_basename = os.path.basename(file_path)

        # Is this the test file?
        is_test_file = test_basename and (
            file_basename == test_basename or
            'debug_this_test' in file_basename or
            'watch_' in file_basename
        )

        # Is this stdlib or third-party?
        is_stdlib = _is_stdlib_or_thirdparty(file_path)

        # Skip runner code (<module>) from test file
        is_runner = is_test_file and method == '<module>'

        if is_runner:
            # Skip runner frames
            continue
        elif is_test_file:
            # Include test file frames (actual test methods)
            relevant_frames.append(frame)
        elif is_stdlib:
            # Stop when we hit stdlib/third-party - don't include these frames
            # But only break if we've already seen at least one frame
            if relevant_frames:
                break
        else:
            # User code - include it
            relevant_frames.append(frame)

    return relevant_frames


def extract_user_error_location(text, test_file):
    """Extract file:line from traceback for the deepest frame NOT in test_file or stdlib.

    Returns (file_path, line_number) or (None, None) if not found.
    """
    # Parse traceback frames: File "path", line N
    frame_pattern = re.compile(r'File "([^"]+)", line (\d+)')
    frames = frame_pattern.findall(text)

    # Filter to user code: not test file, not stdlib, not site-packages
    user_frames = []
    for path, lineno in frames:
        if test_file and os.path.basename(path) == os.path.basename(test_file):
            continue
        if '/lib/python' in path or 'site-packages' in path:
            continue
        if path.startswith('<'):  # <string>, <frozen>, etc.
            continue
        user_frames.append((path, int(lineno)))

    # Return the deepest (last) user frame
    if user_frames:
        return user_frames[-1]
    return None, None


def extract_fail_line(text, target_file, method):
    """Extract the line number from a traceback for a specific file and method.

    Args:
        text: Traceback text to parse
        target_file: File path to match (matches basename)
        method: Method name to match in the "in <method>" part

    Returns:
        Line number as int, or 0 if not found
    """
    # Pattern: File "...", line N, in method_name
    # Use a pattern that handles:
    # - Paths with various characters (but not unescaped quotes)
    # - Method names that may contain brackets like test_foo[param]
    frame_pattern = re.compile(
        r'File "([^"]+)", line (\d+), in (.+?)$',
        re.MULTILINE
    )

    target_basename = os.path.basename(target_file)
    matches = []

    for match in frame_pattern.finditer(text):
        file_path, lineno, frame_method = match.groups()
        frame_method = frame_method.strip()
        file_basename = os.path.basename(file_path)

        # Match by basename to handle different path representations
        if file_basename == target_basename and frame_method == method:
            matches.append(int(lineno))

    # Return the last match (deepest frame in that file/method)
    if matches:
        return matches[-1]
    return 0


def main():
    if len(sys.argv) < 2:
        print('Usage: output_parser.py {crash|source|trace|error|syntax|extract-fail-line|user-error-loc|relevant-tb}', file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'crash':
        print(colorize_crash(sys.stdin.read()))
    elif cmd == 'relevant-tb':
        # Usage: output_parser.py relevant-tb TEST_FILE < traceback
        test_file = sys.argv[2] if len(sys.argv) > 2 else None
        frames = extract_relevant_traceback(sys.stdin.read(), test_file)
        for path, lineno, method in frames:
            print(f'File "{path}", line {lineno}, in {method}')
    elif cmd == 'extract-fail-line':
        # Usage: output_parser.py extract-fail-line TARGET_FILE METHOD < traceback
        if len(sys.argv) < 4:
            print('Usage: output_parser.py extract-fail-line TARGET_FILE METHOD', file=sys.stderr)
            sys.exit(1)
        target_file = sys.argv[2]
        method = sys.argv[3]
        line = extract_fail_line(sys.stdin.read(), target_file, method)
        print(line)
    elif cmd == 'user-error-loc':
        # Usage: output_parser.py user-error-loc TEST_FILE < traceback
        test_file = sys.argv[2] if len(sys.argv) > 2 else None
        path, line = extract_user_error_location(sys.stdin.read(), test_file)
        if path and line:
            print(f'{path}:{line}')
        else:
            print('')
    elif cmd == 'source':
        if len(sys.argv) < 5:
            print('Usage: output_parser.py source FILE METHOD FAIL_LINE', file=sys.stderr)
            sys.exit(1)
        print(extract_source(sys.argv[2], sys.argv[3], int(sys.argv[4])))
    elif cmd == 'trace':
        print(parse_trace(sys.stdin.read()), end='')
    elif cmd == 'error':
        print(colorize_error(sys.stdin.read()))
    elif cmd == 'syntax':
        print(colorize_syntax(sys.stdin.read()), end='')
    else:
        print(f'Unknown command: {cmd}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
