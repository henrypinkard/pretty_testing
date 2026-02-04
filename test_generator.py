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
        print(f"[EXE] {{line}}")
        return audit_trace

    # --- CHECK FOR SKIP LIST (failed-only mode + manual skips) ---
    _skip_tests = set()
    _skip_file = '_pretty_testing_/.skip_tests'
    if os.path.exists(_skip_file):
        with open(_skip_file) as _sf:
            _skip_tests = set(line.strip() for line in _sf if line.strip())
    # Also check for manual skip file
    _manual_skip_file = '_pretty_testing_/.manual_skip'
    if os.path.exists(_manual_skip_file):
        with open(_manual_skip_file) as _msf:
            _skip_tests.update(line.strip() for line in _msf if line.strip())

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
        # Skip tests that previously passed (failed-only mode)
        if method_name in _skip_tests:
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
            if single_method:
                print("___TEST_START___")
                sys.settrace(audit_trace)

            _method_func()

            if single_method:
                sys.settrace(None)
            if _expecting_failure:
                # Test passed when expected to fail — unexpected success
                print("FAILED_METHOD:", method_name)
                continue
            print("passed:", method_name, flush=True)
        except unittest.SkipTest:
            if single_method:
                sys.settrace(None)
            print("skipped:", method_name, flush=True)
        except Exception as e:
            sys.settrace(None)
            # Handle @expectedFailure: flag-based (3.12+) or wrapper-based (older)
            if _expecting_failure or type(e).__name__ == '_ExpectedFailure':
                print("passed:", method_name, flush=True)
                continue
            print("FAILED_METHOD:", method_name, flush=True)

            if single_method:
                print("\\n___FAILURE_SUMMARY_START___")

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
                        relevant_frames = []
                        for f in tb:
                            fn = os.path.basename(f.filename)
                            is_test_file = f.filename == __file__ or 'debug_this_test' in fn or 'watch_' in fn
                            is_stdlib = _is_stdlib(f.filename)
                            # Skip runner code (<module>) from test file
                            is_runner = is_test_file and f.name == '<module>'

                            if is_runner:
                                # Skip runner frames
                                continue
                            elif is_test_file:
                                relevant_frames.append(f)
                            elif is_stdlib:
                                # Stop at stdlib - don't include these frames
                                if relevant_frames:
                                    break
                            else:
                                # User code - include it
                                relevant_frames.append(f)

                        # Print all relevant frames
                        for f in relevant_frames:
                            filename = os.path.basename(f.filename)
                            print(f"File \\"{{filename}}\\", line {{f.lineno}}, in {{f.name}}")
                            if f.line:
                                print(f"    {{f.line}}")
                except:
                    pass

                # --- ROBUST FORMATTING ---
                msg = str(e)
                # Split by newline to ignore the 'diff' that unittest adds
                first_line = msg.split('\\n', 1)[0]

                if " != " in first_line:
                    parts = first_line.split(" != ", 1)
                    if len(parts) == 2:
                        print("AssertionError:")
                        print(f"  Actual:   {{parts[0]}}")
                        print(f"  Expected: {{parts[1]}}")
                    else:
                        print(f"{{type(e).__name__}}: {{e}}")
                else:
                    # Fallback for complex messages
                    print(f"{{type(e).__name__}}: {{e}}")

                print("___FAILURE_SUMMARY_END___\\n")

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