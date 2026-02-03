#!/usr/bin/env python3
"""Tests for debug_prep.py"""
import os
import sys
import textwrap
import tempfile
import unittest

from debug_prep import (
    remove_timeouts,
    neutralize_alarms,
    inject_set_trace,
    inject_setup_trace,
    patch_postmortem,
    run_preflight,
)


class TestRemoveTimeouts(unittest.TestCase):

    def test_timeout_with_parens(self):
        lines = ['    @timeout(5)\n', '    def test_foo(self):\n', '        pass\n']
        result = remove_timeouts(lines)
        self.assertEqual(result, ['    def test_foo(self):\n', '        pass\n'])

    def test_timeout_no_parens(self):
        lines = ['    @timeout\n', '    def test_foo(self):\n', '        pass\n']
        result = remove_timeouts(lines)
        self.assertEqual(result, ['    def test_foo(self):\n', '        pass\n'])

    def test_timeout_with_kwargs(self):
        lines = ['    @timeout(seconds=5)\n', '    def test_foo(self):\n']
        result = remove_timeouts(lines)
        self.assertEqual(result, ['    def test_foo(self):\n'])

    def test_multiple_decorators(self):
        lines = [
            '    @mock.patch("foo")\n',
            '    @timeout(5)\n',
            '    def test_foo(self):\n',
            '        pass\n',
        ]
        result = remove_timeouts(lines)
        self.assertEqual(len(result), 3)
        self.assertIn('@mock.patch', result[0])


class TestNeutralizeAlarms(unittest.TestCase):

    def test_signal_alarm_simple(self):
        lines = ['    signal.alarm(30)\n']
        result = neutralize_alarms(lines)
        self.assertEqual(result, ['    signal.alarm(0)\n'])

    def test_signal_alarm_complex_expr(self):
        """The regex replaces up to the first closing paren, leaving trailing parens."""
        lines = ['    signal.alarm(int(os.environ.get("T", 5)))\n']
        result = neutralize_alarms(lines)
        # [^)]* matches up to first ), so nested parens leave trailing ))
        self.assertEqual(result, ['    signal.alarm(0)))\n'])


class TestInjectSetTrace(unittest.TestCase):

    def _make_lines(self, code):
        return textwrap.dedent(code).splitlines(True)

    def test_basic_injection(self):
        lines = self._make_lines("""\
            class TestFoo:
                def test_bar(self):
                    x = 1
                    assert x == 1
        """)
        result = inject_set_trace(lines, 'test_bar')
        joined = ''.join(result)
        self.assertIn('pudb.set_trace()', joined)
        # set_trace should be before x = 1
        trace_idx = next(i for i, l in enumerate(result) if 'set_trace' in l)
        x_idx = next(i for i, l in enumerate(result) if 'x = 1' in l)
        self.assertLess(trace_idx, x_idx)

    def test_method_not_found_fallback(self):
        lines = self._make_lines("""\
            class TestFoo:
                def test_bar(self):
                    pass
        """)
        result = inject_set_trace(lines, 'nonexistent_method')
        self.assertIn('set_trace', result[0])

    def test_set_break_with_fail_line(self):
        lines = self._make_lines("""\
            class TestFoo:
                def test_bar(self):
                    x = 1
                    y = 2
                    assert x == y
        """)
        result = inject_set_trace(lines, 'test_bar', fail_line=5, abs_path='/tmp/test.py')
        joined = ''.join(result)
        self.assertIn('set_break', joined)
        self.assertIn('/tmp/test.py', joined)

    def test_pdbpp_injection(self):
        lines = self._make_lines("""\
            class TestFoo:
                def test_bar(self):
                    pass
        """)
        result = inject_set_trace(lines, 'test_bar', debugger='pdbpp')
        joined = ''.join(result)
        self.assertIn('import pdb;', joined)
        self.assertIn('pdb.set_trace()', joined)
        self.assertIn('sticky_by_default', joined)
        self.assertNotIn('pudb', joined)


class TestInjectSetupTrace(unittest.TestCase):

    def _make_lines(self, code):
        return textwrap.dedent(code).splitlines(True)

    def test_setup_injection(self):
        lines = self._make_lines("""\
            class TestFoo:
                def setUp(self):
                    self.x = 1
                def test_bar(self):
                    pass
        """)
        result = inject_setup_trace(lines)
        joined = ''.join(result)
        self.assertIn('set_trace', joined)
        # Should be inside setUp, before self.x = 1
        trace_idx = next(i for i, l in enumerate(result) if 'set_trace' in l)
        x_idx = next(i for i, l in enumerate(result) if 'self.x = 1' in l)
        self.assertLess(trace_idx, x_idx)

    def test_classmethod_setup(self):
        lines = self._make_lines("""\
            class TestFoo:
                @classmethod
                def setUp(cls):
                    cls.x = 1
        """)
        # setUp is still a FunctionDef in the AST even with @classmethod
        result = inject_setup_trace(lines)
        joined = ''.join(result)
        self.assertIn('set_trace', joined)

    def test_no_setup_fallback(self):
        lines = self._make_lines("""\
            class TestFoo:
                def test_bar(self):
                    pass
        """)
        result = inject_setup_trace(lines)
        self.assertIn('set_trace', result[0])


class TestPatchPostmortem(unittest.TestCase):

    def test_replaces_raise_with_pudb_postmortem(self):
        lines = [
            '                some code\n',
            '                raise e\n',
            '                more code\n',
        ]
        result = patch_postmortem(lines, 'pudb')
        joined = ''.join(result)
        self.assertNotIn('raise e', joined)
        self.assertIn('pudb.post_mortem', joined)
        self.assertIn('post_mortem', joined)

    def test_replaces_raise_with_pdbpp_postmortem(self):
        lines = ['                raise e\n']
        result = patch_postmortem(lines, 'pdbpp')
        joined = ''.join(result)
        self.assertIn('pdb.post_mortem', joined)
        self.assertNotIn('pudb', joined)

    def test_no_raise_unchanged(self):
        lines = ['    x = 1\n', '    y = 2\n']
        result = patch_postmortem(lines, 'pudb')
        self.assertEqual(lines, result)


class TestPreflight(unittest.TestCase):

    def _write_temp(self, code):
        f = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        f.write(textwrap.dedent(code))
        f.close()
        return f.name

    def test_preflight_success(self):
        path = self._write_temp("""\
            import unittest
            class TestOk(unittest.TestCase):
                def setUp(self):
                    self.x = 1
                def test_a(self):
                    pass
        """)
        try:
            ok, err = run_preflight(path, 'test_a')
            self.assertTrue(ok)
        finally:
            os.unlink(path)

    def test_preflight_import_error(self):
        path = self._write_temp("""\
            import nonexistent_module_xyz
            import unittest
            class TestBad(unittest.TestCase):
                def test_a(self): pass
        """)
        try:
            ok, err = run_preflight(path, 'test_a')
            self.assertFalse(ok)
            self.assertIn('Import error', err)
        finally:
            os.unlink(path)

    def test_preflight_setup_error(self):
        path = self._write_temp("""\
            import unittest
            class TestBad(unittest.TestCase):
                def setUp(self):
                    raise RuntimeError("boom")
                def test_a(self):
                    pass
        """)
        try:
            ok, err = run_preflight(path, 'test_a')
            self.assertFalse(ok)
            self.assertIn('setUp failed', err)
        finally:
            os.unlink(path)


class TestSyntaxCheckPerFile(unittest.TestCase):
    """Verify that py_compile catches errors in each file independently."""

    def test_second_file_syntax_error_detected(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            # First file: valid
            with open(os.path.join(d, 'good.py'), 'w') as f:
                f.write('x = 1\n')
            # Second file: syntax error
            with open(os.path.join(d, 'bad.py'), 'w') as f:
                f.write('def broken(\n')

            # py_compile each file individually (like w does)
            errors = []
            for name in sorted(os.listdir(d)):
                path = os.path.join(d, name)
                r = subprocess.run(
                    ['python3', '-m', 'py_compile', path],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    errors.append(r.stderr)

            self.assertEqual(len(errors), 1)
            self.assertIn('bad.py', errors[0])

    def test_all_valid_no_errors(self):
        import subprocess
        with tempfile.TemporaryDirectory() as d:
            for name in ['a.py', 'b.py']:
                with open(os.path.join(d, name), 'w') as f:
                    f.write('x = 1\n')

            errors = []
            for name in sorted(os.listdir(d)):
                path = os.path.join(d, name)
                r = subprocess.run(
                    ['python3', '-m', 'py_compile', path],
                    capture_output=True, text=True,
                )
                if r.returncode != 0:
                    errors.append(r.stderr)

            self.assertEqual(len(errors), 0)


class TestExtractUserErrorLocation(unittest.TestCase):
    """Test output_parser.extract_user_error_location."""

    def test_finds_user_code_error(self):
        from output_parser import extract_user_error_location
        traceback = """\
Traceback (most recent call last):
  File "custom/debug_this_test.py", line 10, in test_foo
    result = my_module.do_thing()
  File "/home/user/project/my_module.py", line 42, in do_thing
    raise ValueError("oops")
ValueError: oops
"""
        path, line = extract_user_error_location(traceback, "debug_this_test.py")
        self.assertEqual(path, "/home/user/project/my_module.py")
        self.assertEqual(line, 42)

    def test_ignores_stdlib(self):
        from output_parser import extract_user_error_location
        traceback = """\
Traceback (most recent call last):
  File "custom/debug_this_test.py", line 10, in test_foo
    json.loads(bad)
  File "/usr/lib/python3.10/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
JSONDecodeError: Expecting value
"""
        path, line = extract_user_error_location(traceback, "debug_this_test.py")
        self.assertIsNone(path)

    def test_returns_none_when_only_test_file(self):
        from output_parser import extract_user_error_location
        traceback = """\
Traceback (most recent call last):
  File "custom/debug_this_test.py", line 10, in test_foo
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        path, line = extract_user_error_location(traceback, "debug_this_test.py")
        self.assertIsNone(path)


if __name__ == '__main__':
    unittest.main()
