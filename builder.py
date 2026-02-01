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
    
    # --- UNIVERSAL DISCOVERY ---
    target_class = None
    current_module = sys.modules[__name__]
    for name, obj in inspect.getmembers(current_module):
        if inspect.isclass(obj) and issubclass(obj, unittest.TestCase):
            if obj is not unittest.TestCase:
                target_class = obj
                break
    
    if not target_class:
        print("NO_TEST_CLASS_FOUND")
        sys.exit(0)

    loader = unittest.TestLoader()
    try:
        available_methods = loader.getTestCaseNames(target_class)
    except Exception as e:
        print("ERROR_LOADING_TESTS:", e)
        sys.exit(1)

    target_method = {target_method_repr}
    if target_method:
        methods = [target_method] if target_method in available_methods else []
    else:
        methods = available_methods

    if not methods:
        print("NO_TESTS_FOUND_IN_FILE")
        sys.exit(0)

    if len(sys.argv) > 1:
         method_to_run = sys.argv[1]
         if method_to_run in methods:
             methods = [method_to_run]
    
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

    for method_name in methods:
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

        try:
            if len(methods) == 1:
                print("___TEST_START___")
                sys.settrace(audit_trace)
            
            getattr(test_instance, method_name)()
            
            if len(methods) == 1:
                sys.settrace(None)
            print("passed:", method_name)
        except Exception as e:
            sys.settrace(None)
            print("FAILED_METHOD:", method_name)
            
            if len(methods) == 1:
                print("\\n___FAILURE_SUMMARY_START___")
                
                try:
                    tb = traceback.extract_tb(e.__traceback__)
                    if tb:
                        # Walk backwards to find the frame in the user's test file,
                        # not inside unittest internals like case.py
                        frame = tb[-1]
                        for f in reversed(tb):
                            if f.filename == __file__ or 'my_test' in os.path.basename(f.filename) or 'watch_' in os.path.basename(f.filename):
                                frame = f
                                break
                        filename = os.path.basename(frame.filename)
                        print(f"File \\"{{filename}}\\", line {{frame.lineno}}")
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
        dest_file = os.path.join("custom", "my_test.py")
        only_test_method = sys.argv[2]
    else:
        base = os.path.basename(test_file)
        stem = os.path.splitext(base)[0]
        dest_file = os.path.join("custom", f"my_{stem}.py")
        only_test_method = None

    generate_standalone_test(test_file, dest_file, only_test_method)

if __name__ == "__main__":
    main()