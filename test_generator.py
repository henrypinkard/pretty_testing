#!/usr/bin/env python3
"""
Generates a standalone version of a test file.
Refactored: Robust Expected/Actual formatting (ignores unittest diff noise).
"""
import re
import sys
import os
import inspect
import unittest
import linecache
import traceback

# --- THE MAGIC TIMEOUT HELPER ---
TIMEOUT_CODE = """
import signal
from functools import wraps

class TimeoutError(Exception):
    pass

def timeout(seconds=1):
    '''Auto-injected timeout decorator.'''
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            def handler(signum, frame):
                raise TimeoutError(f"Test timed out after {seconds}s")
            signal.signal(signal.SIGALRM, handler)
            sec_int = int(seconds) if int(seconds) > 0 else 1
            signal.alarm(sec_int)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
        return wrapper
    return decorator
"""

def generate_standalone_test(test_file, dest_file, only_test_method=None):
    if not os.path.exists(test_file):
        sys.exit(1)

    try:
        with open(test_file, "r") as f:
            source_lines = f.readlines()
            content = "".join(source_lines)
    except Exception:
        sys.exit(1)

    # --- 1. CLEANUP ---
    try:
        content = re.sub(r"if __name__\s*==\s*['\"]__main__['\"]:\s*.*", "", content, flags=re.DOTALL)
        source_lines = content.splitlines(keepends=True)
    except Exception:
        pass

    test_dir_abs = os.path.dirname(os.path.abspath(test_file))
    repo_root_abs = os.path.dirname(test_dir_abs)
    
    # --- 2. PREPARE BLOCKS ---
    target_method_repr = f"'{only_test_method}'" if only_test_method else "None"

    # PATH SETUP (Crucial for imports)
    PATH_SETUP_BLOCK = f"""
import sys
import os
sys.path.insert(0, r'{repo_root_abs}')
sys.path.insert(0, r'{test_dir_abs}')
"""

    RUNNER_BLOCK = f"""

if __name__ == '__main__':
    import linecache
    import unittest
    import inspect
    import traceback

    # --- DISCOVER ALL TEST CLASSES ---
    current_module = sys.modules[__name__]
    test_classes = []
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            if obj is not unittest.TestCase:
                test_classes.append(obj)

    if not test_classes:
        print("NO_TEST_CLASS_FOUND", flush=True)
        sys.exit(0)

    # --- BUILD (class, method) PAIRS ---
    target_method = {target_method_repr}
    pairs = []
    for _cls in test_classes:
        _loader = unittest.TestLoader()
        try:
            _cls_methods = _loader.getTestCaseNames(_cls)
        except Exception as e:
            print("ERROR_LOADING_TESTS:", e)
            continue
        if target_method:
            if target_method in _cls_methods:
                pairs = [(_cls, target_method)]
                break
        else:
            for _m in _cls_methods:
                pairs.append((_cls, _m))

    if not pairs:
        print("NO_TESTS_FOUND_IN_FILE", flush=True)
        sys.exit(0)

    if len(sys.argv) > 1:
         method_to_run = sys.argv[1]
         pairs = [(_c, _m) for _c, _m in pairs if _m == method_to_run]

    methods = [_m for _, _m in pairs]
    single_method = len(pairs) == 1

    def audit_trace(frame, event, arg):
        if event != 'line': return audit_trace
        if frame.f_code.co_name not in methods: return audit_trace
        lineno = frame.f_lineno
        filename = frame.f_code.co_filename
        try:
            line = linecache.getline(filename, lineno).strip()
        except:
            line = "???"
        # Skip debugger setup lines
        if any(x in line for x in ['pudb', 'pdb', '_dbg', 'set_break', 'set_trace', '_es=', '.error_summary']):
            return audit_trace
        print(f"[EXE] {{line}}")
        return audit_trace

    # --- FAILED-ONLY MODE: filter pairs to just the failed tests ---
    _run_file = '_pretty_testing_/.run_tests'
    if os.path.exists(_run_file):
        with open(_run_file) as _rf:
            _run_only = set(line.strip() for line in _rf if line.strip())
        pairs = [(_c, _m) for _c, _m in pairs if _m in _run_only]
        methods = [_m for _, _m in pairs]
        single_method = len(pairs) == 1

    # Manual skip: user-chosen skips — visible on dashboard
    _manual_skip = set()
    _manual_skip_file = '_pretty_testing_/.manual_skip'
    if os.path.exists(_manual_skip_file):
        with open(_manual_skip_file) as _msf:
            _manual_skip = set(line.strip() for line in _msf if line.strip())

    # --- setUpModule ---
    if hasattr(current_module, 'setUpModule'):
        try:
            current_module.setUpModule()
        except Exception as _e:
            for _, _m in pairs:
                print("FAILED_METHOD:", _m)
                print(f"  (setUpModule failed: {{_e}})")
            sys.exit(1)

    # --- setUpClass TRACKING ---
    _setup_done = set()
    _setup_failed = set()
    _teardown_classes = []

    for target_class, method_name in pairs:
        # Visible skip: manually skipped tests
        if method_name in _manual_skip:
            print("skipped:", method_name, flush=True)
            continue

        # Skip all methods from a class whose setUpClass failed
        if target_class in _setup_failed:
            print("FAILED_METHOD:", method_name)
            print("  (setUpClass failed for this class)")
            continue

        # Call setUpClass once per class
        if target_class not in _setup_done:
            _setup_done.add(target_class)
            _teardown_classes.append(target_class)
            try:
                target_class.setUpClass()
            except Exception as _e:
                _setup_failed.add(target_class)
                print("FAILED_METHOD:", method_name)
                print(f"  (setUpClass failed: {{_e}})")
                continue

        try:
            test_instance = target_class(method_name)
        except:
            test_instance = target_class()

        try:
            if hasattr(test_instance, 'setUp'):
                test_instance.setUp()
        except Exception as e:
            print("FAILED_METHOD:", method_name)
            print(f"  (setUp failed: {{e}})")
            continue

        _method_func = getattr(test_instance, method_name)
        _expecting_failure = getattr(_method_func, '__unittest_expecting_failure__', False)

        try:
            _debug_mode = os.environ.get('PRETTY_TESTING_DEBUG') == '1'
            if single_method and not _debug_mode:
                print("___TEST_START___")
                sys.settrace(audit_trace)

            # Per-test timeout (env var set by w, skipped in debug mode)
            _timeout_sec = 0
            if not _debug_mode:
                try:
                    _timeout_sec = int(os.environ.get('PRETTY_TESTING_TIMEOUT', '0'))
                except ValueError:
                    _timeout_sec = 0
            if _timeout_sec > 0:
                def _timeout_handler(signum, frame):
                    raise TimeoutError(f"Timed out after {{_timeout_sec}}s")
                signal.signal(signal.SIGALRM, _timeout_handler)
                signal.alarm(_timeout_sec)

            _method_func()

            if _timeout_sec > 0:
                signal.alarm(0)
            if single_method:
                sys.settrace(None)
            if _expecting_failure:
                # Test passed when expected to fail — unexpected success
                print("FAILED_METHOD:", method_name)
                continue
            print("passed:", method_name, flush=True)
        except unittest.SkipTest:
            signal.alarm(0)
            if single_method:
                sys.settrace(None)
            print("skipped:", method_name, flush=True)
        except Exception as e:
            signal.alarm(0)
            sys.settrace(None)
            # Handle @expectedFailure: flag-based (3.12+) or wrapper-based (older)
            if _expecting_failure or type(e).__name__ == '_ExpectedFailure':
                print("passed:", method_name, flush=True)
                continue
            print("FAILED_METHOD:", method_name, flush=True)

            if single_method:
                print("\\n___FAILURE_SUMMARY_START___")

                # ANSI color codes
                _c_reset = "\\033[0m"
                _c_dim = "\\033[2m"
                _c_bold = "\\033[1m"
                _c_red = "\\033[31m"
                _c_green = "\\033[32m"
                _c_yellow = "\\033[33m"
                _c_blue = "\\033[34m"
                _c_magenta = "\\033[35m"
                _c_cyan = "\\033[36m"

                def _highlight_code(code):
                    '''Simple syntax highlighting for a line of code.'''
                    import re
                    # Strings (double or single quoted)
                    code = re.sub(r'("[^"]*")', _c_green + r'\\1' + _c_reset, code)
                    code = re.sub(r"('[^']*')", _c_green + r'\\1' + _c_reset, code)
                    # Numbers
                    code = re.sub(r'\\b(\\d+)\\b', _c_cyan + r'\\1' + _c_reset, code)
                    # Keywords
                    keywords = r'\\b(def|class|return|if|else|elif|while|for|in|try|except|raise|import|from|as|pass|None|True|False|self|with|lambda|yield|assert)\\b'
                    code = re.sub(keywords, _c_yellow + r'\\1' + _c_reset, code)
                    return code

                relevant_frames = []
                try:
                    tb = traceback.extract_tb(e.__traceback__)
                    if tb:
                        # Helper to check if path is stdlib or third-party
                        def _is_stdlib(path):
                            if path.startswith('<'):
                                return True
                            if '/lib/python' in path or '\\\\lib\\\\python' in path:
                                return True
                            if 'site-packages' in path or 'dist-packages' in path:
                                return True
                            return False

                        # Extract relevant frames: test file + user code, stop at stdlib
                        for f in tb:
                            fn = os.path.basename(f.filename)
                            is_test_file = f.filename == __file__ or 'debug_this_test' in fn or 'watch_' in fn
                            is_stdlib = _is_stdlib(f.filename)
                            # Skip runner code (<module>) from test file
                            is_runner = is_test_file and f.name == '<module>'

                            if is_runner:
                                continue
                            elif is_test_file:
                                relevant_frames.append(f)
                            elif is_stdlib:
                                if relevant_frames:
                                    break
                            else:
                                relevant_frames.append(f)

                        # Cap frames for deep recursion
                        _MAX_DISPLAY_FRAMES = 10
                        _truncated = len(relevant_frames) > _MAX_DISPLAY_FRAMES
                        if _truncated:
                            _show = relevant_frames[:3] + relevant_frames[-3:]
                            _omitted = len(relevant_frames) - 6
                        else:
                            _show = relevant_frames

                        # Print stack trace with compact tree connectors
                        print(f"{{_c_dim}}Traceback (from test to error):{{_c_reset}}")
                        for i, f in enumerate(_show):
                            filename = os.path.basename(f.filename)
                            indent = "   " * min(i, 5)  # cap indent depth

                            # Show omission marker between first and last groups
                            if _truncated and i == 3:
                                print(f"{{indent}}{{_c_dim}}   ... {{_omitted}} frames omitted (recursive) ...{{_c_reset}}")

                            # Frame header (with arrow prefix if not first)
                            if i == 0:
                                print(f"{{_c_blue}}{{filename}}{{_c_reset}}:{{_c_green}}{{f.lineno}}{{_c_reset}} in {{_c_yellow}}{{f.name}}{{_c_reset}}")
                            else:
                                print(f"{{indent}}{{_c_dim}}└►{{_c_reset}} {{_c_blue}}{{filename}}{{_c_reset}}:{{_c_green}}{{f.lineno}}{{_c_reset}} in {{_c_yellow}}{{f.name}}{{_c_reset}}")
                            if f.line:
                                highlighted = _highlight_code(f.line)
                                print(f"{{indent}}   {{highlighted}}")
                        print()  # blank line before error
                except:
                    pass

                # --- ERROR MESSAGE AT BOTTOM ---
                msg = str(e)
                first_line = msg.split('\\n', 1)[0]

                if " != " in first_line:
                    parts = first_line.split(" != ", 1)
                    if len(parts) == 2:
                        print(f"{{_c_bold}}{{_c_red}}AssertionError:{{_c_reset}}")
                        print(f"  {{_c_bold}}Actual:   {{_c_yellow}}{{parts[0]}}{{_c_reset}}")
                        print(f"  {{_c_bold}}Expected: {{_c_green}}{{parts[1]}}{{_c_reset}}")
                    else:
                        print(f"{{_c_bold}}{{_c_red}}{{type(e).__name__}}:{{_c_reset}} {{e}}")
                else:
                    print(f"{{_c_bold}}{{_c_red}}{{type(e).__name__}}:{{_c_reset}} {{e}}")

                print("___FAILURE_SUMMARY_END___\\n")

                if not isinstance(e, RecursionError):
                    raise e
            pass
        finally:
             if hasattr(test_instance, 'tearDown'):
                 try: test_instance.tearDown()
                 except: pass

    # --- tearDownClass ---
    for _cls in _teardown_classes:
        if _cls not in _setup_failed:
            try:
                _cls.tearDownClass()
            except:
                pass

    # --- tearDownModule ---
    if hasattr(current_module, 'tearDownModule'):
        try:
            current_module.tearDownModule()
        except:
            pass
    """
    
    try:
        with open(dest_file, "w") as f:
            f.write(PATH_SETUP_BLOCK + "\n")
            f.write(TIMEOUT_CODE + "\n")
            f.write(content)
            f.write(RUNNER_BLOCK)
        print(f"Standalone test file generated: {dest_file}")
    except Exception as e:
        print("Error writing to destination file:", e)
        sys.exit(1)

def main():
    if len(sys.argv) < 2: sys.exit(1)
    test_file = sys.argv[1]
    if len(sys.argv) == 3:
        dest_file = os.path.join("_pretty_testing_", "debug_this_test.py")
        only_test_method = sys.argv[2]
    else:
        base = os.path.basename(test_file)
        stem = os.path.splitext(base)[0]
        dest_file = os.path.join("_pretty_testing_", f"debug_this_test_{stem}.py")
        only_test_method = None

    generate_standalone_test(test_file, dest_file, only_test_method)

if __name__ == "__main__":
    main()