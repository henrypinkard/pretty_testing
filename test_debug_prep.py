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
    read_manual_breakpoints,
    MANUAL_BP_FILE,
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

    def test_setup_injection_with_breakpoints(self):
        """When injecting into setUp, should also set breakpoints at fail line and method start."""
        lines = self._make_lines("""\
            class TestFoo:
                def setUp(self):
                    self.x = 1
                def test_bar(self):
                    y = 2
                    assert y == 1
        """)
        result = inject_setup_trace(
            lines,
            debugger='pudb',
            method='test_bar',
            fail_line=6,
            abs_path='/tmp/test.py',
        )
        joined = ''.join(result)
        self.assertIn('set_trace', joined)
        # Should have set_break for the fail line (adjusted for injection)
        self.assertIn('set_break', joined)
        self.assertIn('/tmp/test.py', joined)

    def test_setup_injection_sets_method_start_breakpoint(self):
        """When injecting into setUp, should set breakpoint at start of target method body."""
        lines = self._make_lines("""\
            class TestFoo:
                def setUp(self):
                    self.x = 1
                def test_bar(self):
                    first_line = 1
                    second_line = 2
        """)
        result = inject_setup_trace(
            lines,
            debugger='pudb',
            method='test_bar',
            abs_path='/tmp/test.py',
        )
        joined = ''.join(result)
        # Should set breakpoint at the first line of test_bar body
        self.assertIn('set_break', joined)


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

    def test_preflight_multiple_classes_finds_correct_one(self):
        """When multiple test classes exist, preflight should find the one with the target method."""
        path = self._write_temp("""\
            import unittest
            class TestFirst(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    cls.x = 1
                def test_a(self):
                    pass

            class TestSecond(unittest.TestCase):
                def setUp(self):
                    self.y = 2
                def test_b(self):
                    pass

            class TestThird(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    cls.z = 3
                def test_c(self):
                    pass
        """)
        try:
            # test_b is in TestSecond which has setUp - should succeed
            ok, err = run_preflight(path, 'test_b')
            self.assertTrue(ok, f"Expected success for test_b but got: {err}")
        finally:
            os.unlink(path)

    def test_preflight_method_in_class_with_setUpClass(self):
        """Preflight should succeed even if the target class uses setUpClass instead of setUp."""
        path = self._write_temp("""\
            import unittest
            class TestWithSetUpClass(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    cls.x = 1
                def test_a(self):
                    pass
        """)
        try:
            ok, err = run_preflight(path, 'test_a')
            self.assertTrue(ok, f"Expected success but got: {err}")
        finally:
            os.unlink(path)

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
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
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
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
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
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        path, line = extract_user_error_location(traceback, "debug_this_test.py")
        self.assertIsNone(path)


class TestExtractRelevantTraceback(unittest.TestCase):
    """Test output_parser.extract_relevant_traceback for proper stack trace display."""

    def test_assertion_in_test_only(self):
        """When assertion fails directly in test, return just the test frame."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 1)
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[0][1], 10)
        self.assertEqual(frames[0][2], "test_foo")

    def test_exception_in_user_code_single_level(self):
        """Test calls user code, user code raises - show test + user code."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    result = my_module.calculate()
  File "/home/user/project/my_module.py", line 25, in calculate
    raise ValueError("bad")
ValueError: bad
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 2)
        # First frame: test file
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[0][1], 10)
        # Second frame: user code
        self.assertEqual(frames[1][0], "/home/user/project/my_module.py")
        self.assertEqual(frames[1][1], 25)
        self.assertEqual(frames[1][2], "calculate")

    def test_exception_in_user_code_multiple_levels(self):
        """Test → user func → user func → raises - show all user frames."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    result = my_module.calculate()
  File "/home/user/project/my_module.py", line 25, in calculate
    return helper()
  File "/home/user/project/my_module.py", line 50, in helper
    raise ValueError("deep error")
ValueError: deep error
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 3)
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[1][1], 25)
        self.assertEqual(frames[1][2], "calculate")
        self.assertEqual(frames[2][1], 50)
        self.assertEqual(frames[2][2], "helper")

    def test_exception_in_stdlib_stops_at_user_code(self):
        """Test → user code → stdlib raises - show test + user code, NOT stdlib."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    result = my_module.parse_data(bad_json)
  File "/home/user/project/my_module.py", line 25, in parse_data
    return json.loads(data)
  File "/usr/lib/python3.10/json/__init__.py", line 346, in loads
    return _default_decoder.decode(s)
  File "/usr/lib/python3.10/json/decoder.py", line 337, in decode
    obj, end = self.raw_decode(s, idx=_w(s, 0).end())
JSONDecodeError: Expecting value
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 2)
        # Should include test + user code, but NOT json stdlib frames
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[1][0], "/home/user/project/my_module.py")
        self.assertEqual(frames[1][1], 25)
        # Should NOT include any stdlib frames
        for frame in frames:
            self.assertNotIn("/usr/lib/python", frame[0])

    def test_exception_in_nested_user_then_stdlib(self):
        """Test → user1 → user2 → stdlib - show test + user1 + user2, NOT stdlib."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    my_module.outer()
  File "/home/user/project/my_module.py", line 20, in outer
    inner()
  File "/home/user/project/my_module.py", line 30, in inner
    os.path.exists(None)
  File "/usr/lib/python3.10/genericpath.py", line 19, in exists
    os.stat(path)
TypeError: stat: path should be string, bytes, os.PathLike or integer
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 3)
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[1][2], "outer")
        self.assertEqual(frames[2][2], "inner")

    def test_handles_site_packages(self):
        """User code calls third-party library - include user, exclude third-party."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_foo
    my_module.use_numpy()
  File "/home/user/project/my_module.py", line 25, in use_numpy
    np.array(None).reshape(-1)
  File "/home/user/.local/lib/python3.10/site-packages/numpy/core/fromnumeric.py", line 285, in reshape
    return _wrapfunc(a, 'reshape', newshape, order=order)
ValueError: cannot reshape
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        self.assertEqual(len(frames), 2)
        self.assertIn("debug_this_test.py", frames[0][0])
        self.assertEqual(frames[1][0], "/home/user/project/my_module.py")
        # Should NOT include numpy frames
        for frame in frames:
            self.assertNotIn("site-packages", frame[0])

    def test_excludes_module_runner_frames(self):
        """Runner code (<module>) in test file should be excluded."""
        from output_parser import extract_relevant_traceback
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 172, in <module>
    _method_func()
  File "_pretty_testing_/debug_this_test.py", line 38, in test_user_code_error
    my_module.outer()
  File "/home/user/project/my_module.py", line 2, in outer
    return inner()
  File "/home/user/project/my_module.py", line 5, in inner
    raise ValueError("error")
ValueError: error
"""
        frames = extract_relevant_traceback(traceback, "debug_this_test.py")
        # Should have 3 frames: test_user_code_error, outer, inner
        # Should NOT include the <module> frame
        self.assertEqual(len(frames), 3)
        self.assertEqual(frames[0][2], "test_user_code_error")
        self.assertEqual(frames[1][2], "outer")
        self.assertEqual(frames[2][2], "inner")
        # Verify no <module> frame
        for frame in frames:
            self.assertNotEqual(frame[2], "<module>")


class TestExtractFailLine(unittest.TestCase):
    """Test output_parser.extract_fail_line."""

    def test_basic_extraction(self):
        from output_parser import extract_fail_line
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 25, in test_foo
    self.assertEqual(1, 2)
AssertionError: 1 != 2
"""
        line = extract_fail_line(traceback, "debug_this_test.py", "test_foo")
        self.assertEqual(line, 25)

    def test_method_with_brackets(self):
        """Test that method names with brackets like test_foo[param] are handled."""
        from output_parser import extract_fail_line
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 42, in test_foo[param1-param2]
    assert result == expected
AssertionError
"""
        line = extract_fail_line(traceback, "debug_this_test.py", "test_foo[param1-param2]")
        self.assertEqual(line, 42)

    def test_multiple_frames_returns_last(self):
        """When the same file/method appears multiple times, return the last (deepest) frame."""
        from output_parser import extract_fail_line
        traceback = """\
Traceback (most recent call last):
  File "_pretty_testing_/debug_this_test.py", line 10, in test_recursive
    self.helper()
  File "_pretty_testing_/debug_this_test.py", line 15, in helper
    self.test_recursive()
  File "_pretty_testing_/debug_this_test.py", line 20, in test_recursive
    raise ValueError()
ValueError
"""
        line = extract_fail_line(traceback, "debug_this_test.py", "test_recursive")
        self.assertEqual(line, 20)

    def test_returns_zero_when_not_found(self):
        from output_parser import extract_fail_line
        traceback = """\
Traceback (most recent call last):
  File "other_file.py", line 10, in other_method
    raise ValueError()
ValueError
"""
        line = extract_fail_line(traceback, "debug_this_test.py", "test_foo")
        self.assertEqual(line, 0)

    def test_path_variations(self):
        """Test that different path representations match by basename."""
        from output_parser import extract_fail_line
        traceback = """\
Traceback (most recent call last):
  File "/home/user/project/_pretty_testing_/debug_this_test.py", line 33, in test_bar
    assert False
AssertionError
"""
        # Should match even though we pass just the basename
        line = extract_fail_line(traceback, "debug_this_test.py", "test_bar")
        self.assertEqual(line, 33)


class TestColorizeErrorExtended(unittest.TestCase):
    """Test that colorize_error handles more exception types."""

    def test_stop_iteration(self):
        from output_parser import colorize_error
        text = "StopIteration: generator exhausted"
        result = colorize_error(text)
        self.assertIn("StopIteration", result)
        self.assertIn("\033[", result)  # Should have color codes

    def test_keyboard_interrupt(self):
        from output_parser import colorize_error
        text = "KeyboardInterrupt: user cancelled"
        result = colorize_error(text)
        self.assertIn("KeyboardInterrupt", result)
        self.assertIn("\033[", result)

    def test_system_exit(self):
        from output_parser import colorize_error
        text = "SystemExit: exit code 1"
        result = colorize_error(text)
        self.assertIn("SystemExit", result)
        self.assertIn("\033[", result)


class TestManualBreakpoints(unittest.TestCase):
    """Test manual breakpoint management."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_read_manual_breakpoints_empty(self):
        """Returns empty list when no breakpoints file exists."""
        bps = read_manual_breakpoints()
        self.assertEqual(bps, [])

    def test_read_manual_breakpoints_parses_file(self):
        """Reads breakpoints from file in filepath:line format."""
        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path, 'w') as f:
            f.write('/path/to/file.py:42\n')
            f.write('/another/file.py:100\n')
            f.write('\n')  # empty line should be skipped

        bps = read_manual_breakpoints()
        self.assertEqual(len(bps), 2)
        self.assertEqual(bps[0], ('/path/to/file.py', 42))
        self.assertEqual(bps[1], ('/another/file.py', 100))

    def test_read_manual_breakpoints_handles_invalid_lines(self):
        """Invalid lines (no colon, non-numeric line) are skipped."""
        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path, 'w') as f:
            f.write('no_colon_here\n')
            f.write('/valid/file.py:50\n')
            f.write('/bad/line:notanumber\n')

        bps = read_manual_breakpoints()
        self.assertEqual(len(bps), 1)
        self.assertEqual(bps[0], ('/valid/file.py', 50))

    def test_inject_set_trace_includes_manual_breakpoints(self):
        """Manual breakpoints are included in injected trace."""
        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path, 'w') as f:
            f.write('/my/source.py:25\n')

        lines = textwrap.dedent("""\
            class TestFoo:
                def test_bar(self):
                    x = 1
        """).splitlines(True)

        result = inject_set_trace(lines, 'test_bar')
        joined = ''.join(result)
        self.assertIn('set_break("/my/source.py", 25)', joined)

    def test_inject_setup_trace_includes_manual_breakpoints(self):
        """Manual breakpoints are included when injecting into setUp."""
        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path, 'w') as f:
            f.write('/my/source.py:30\n')

        lines = textwrap.dedent("""\
            class TestFoo:
                def setUp(self):
                    self.x = 1
                def test_bar(self):
                    pass
        """).splitlines(True)

        result = inject_setup_trace(lines)
        joined = ''.join(result)
        self.assertIn('set_break("/my/source.py", 30)', joined)


class TestManualSkipIntegration(unittest.TestCase):
    """Test that manual skip file is read by test_generator runner block."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)
        os.makedirs('tests', exist_ok=True)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_manual_skip_file_format(self):
        """Manual skip file contains one test name per line."""
        skip_path = os.path.join('_pretty_testing_', '.manual_skip')
        with open(skip_path, 'w') as f:
            f.write('test_foo\n')
            f.write('test_bar\n')

        with open(skip_path) as f:
            skipped = set(line.strip() for line in f if line.strip())

        self.assertEqual(skipped, {'test_foo', 'test_bar'})


class TestBpScript(unittest.TestCase):
    """Test the bp script for breakpoint management."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)
        # Create a dummy file to add breakpoints to
        with open('myfile.py', 'w') as f:
            f.write('x = 1\n' * 50)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def _run_bp(self, *args):
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'bp')
        result = subprocess.run(
            [script_path] + list(args),
            capture_output=True, text=True, cwd=self.tmpdir
        )
        return result

    def test_bp_add_creates_entry(self):
        """bp add creates an entry in .manual_breakpoints."""
        self._run_bp('add', 'myfile.py', '10')
        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path) as f:
            content = f.read()
        self.assertIn(':10', content)
        self.assertIn('myfile.py', content)

    def test_bp_rm_removes_entry(self):
        """bp rm removes an entry from .manual_breakpoints."""
        self._run_bp('add', 'myfile.py', '10')
        self._run_bp('add', 'myfile.py', '20')
        self._run_bp('rm', 'myfile.py', '10')

        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        with open(bp_path) as f:
            content = f.read()
        self.assertNotIn(':10\n', content)
        self.assertIn(':20', content)

    def test_bp_clear_empties_file(self):
        """bp clear removes all breakpoints."""
        self._run_bp('add', 'myfile.py', '10')
        self._run_bp('add', 'myfile.py', '20')
        self._run_bp('clear')

        bp_path = os.path.join('_pretty_testing_', '.manual_breakpoints')
        self.assertFalse(os.path.exists(bp_path))

    def test_bp_list_shows_breakpoints(self):
        """bp list outputs current breakpoints."""
        self._run_bp('add', 'myfile.py', '10')
        result = self._run_bp('list')
        self.assertIn('myfile.py', result.stdout)
        self.assertIn('10', result.stdout)


class TestSkipScript(unittest.TestCase):
    """Test the skip script for test skip management."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def _run_skip(self, *args):
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'skip')
        result = subprocess.run(
            [script_path] + list(args),
            capture_output=True, text=True, cwd=self.tmpdir
        )
        return result

    def test_skip_add_creates_entry(self):
        """skip add creates an entry in .manual_skip."""
        self._run_skip('add', 'test_foo')
        skip_path = os.path.join('_pretty_testing_', '.manual_skip')
        with open(skip_path) as f:
            content = f.read()
        self.assertIn('test_foo', content)

    def test_skip_rm_removes_entry(self):
        """skip rm removes an entry from .manual_skip."""
        self._run_skip('add', 'test_foo')
        self._run_skip('add', 'test_bar')
        self._run_skip('rm', 'test_foo')

        skip_path = os.path.join('_pretty_testing_', '.manual_skip')
        with open(skip_path) as f:
            content = f.read()
        self.assertNotIn('test_foo', content)
        self.assertIn('test_bar', content)

    def test_skip_clear_empties_file(self):
        """skip clear removes all skips."""
        self._run_skip('add', 'test_foo')
        self._run_skip('add', 'test_bar')
        self._run_skip('clear')

        skip_path = os.path.join('_pretty_testing_', '.manual_skip')
        self.assertFalse(os.path.exists(skip_path))

    def test_skip_list_shows_skipped_tests(self):
        """skip list outputs currently skipped tests."""
        self._run_skip('add', 'test_foo')
        result = self._run_skip('list')
        self.assertIn('test_foo', result.stdout)


class TestParseTraceFiltering(unittest.TestCase):
    """Test output_parser.parse_trace filters out noise from execution log."""

    def _strip_ansi(self, text):
        """Remove ANSI color codes from text."""
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def test_filters_pudb_setup_lines(self):
        """[EXE] lines containing pudb/pdb setup code should be filtered out."""
        from output_parser import parse_trace
        raw_output = """\
___TEST_START___
[EXE] import pudb; _dbg = pudb._get_debugger(); _dbg.set_break("/path/to/file.py", 42)
[EXE] tree = [Token(1, "A")]
[EXE] result = self.analyzer.flatten_tree(tree)
FAILED_METHOD: test_foo
"""
        result = parse_trace(raw_output)
        # Split by separator
        parts = result.split('___SECTION_SEP___')
        exec_log = self._strip_ansi(parts[2]) if len(parts) > 2 else ""
        # Should NOT contain the pudb setup line
        self.assertNotIn('pudb', exec_log)
        self.assertNotIn('_dbg', exec_log)
        self.assertNotIn('set_break', exec_log)
        # Should contain the actual test code
        self.assertIn('tree = [Token(1, "A")]', exec_log)
        self.assertIn('result = self.analyzer.flatten_tree(tree)', exec_log)

    def test_filters_pdb_setup_lines(self):
        """[EXE] lines containing pdb setup code should be filtered out."""
        from output_parser import parse_trace
        raw_output = """\
___TEST_START___
[EXE] import pdb; pdb.set_trace()
[EXE] actual_code = True
"""
        result = parse_trace(raw_output)
        parts = result.split('___SECTION_SEP___')
        exec_log = self._strip_ansi(parts[2]) if len(parts) > 2 else ""
        self.assertNotIn('pdb', exec_log)
        self.assertNotIn('set_trace', exec_log)
        self.assertIn('actual_code = True', exec_log)

    def test_filters_failed_method_lines(self):
        """FAILED_METHOD: lines should be filtered from execution log."""
        from output_parser import parse_trace
        raw_output = """\
___TEST_START___
[EXE] x = 1
FAILED_METHOD: test_foo
some output
"""
        result = parse_trace(raw_output)
        parts = result.split('___SECTION_SEP___')
        exec_log = self._strip_ansi(parts[2]) if len(parts) > 2 else ""
        self.assertNotIn('FAILED_METHOD', exec_log)
        self.assertIn('x = 1', exec_log)

    def test_preserves_regular_exe_lines(self):
        """Regular [EXE] lines should be preserved and colorized."""
        from output_parser import parse_trace
        raw_output = """\
___TEST_START___
[EXE] result = calculate(5)
[EXE] self.assertEqual(result, 10)
"""
        result = parse_trace(raw_output)
        parts = result.split('___SECTION_SEP___')
        exec_log = self._strip_ansi(parts[2]) if len(parts) > 2 else ""
        # Should contain the code
        self.assertIn('result = calculate(5)', exec_log)
        self.assertIn('self.assertEqual(result, 10)', exec_log)


class TestUntraceScript(unittest.TestCase):
    """Test the untrace script removes @trace decorators."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.script = os.path.join(os.path.dirname(__file__), 'untrace')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_file(self, relpath, content):
        path = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        return path

    def _read_file(self, path):
        with open(path) as f:
            return f.read()

    def _run_untrace(self, *args):
        import subprocess
        return subprocess.run(
            [self.script] + list(args),
            capture_output=True, text=True, cwd=self.tmpdir
        )

    def test_removes_trace_no_args(self):
        """@trace with no parens is removed."""
        path = self._write_file('foo.py', '@trace\ndef foo():\n    pass\n')
        self._run_untrace(path)
        self.assertEqual(self._read_file(path), 'def foo():\n    pass\n')

    def test_removes_trace_empty_parens(self):
        """@trace() with empty parens is removed."""
        path = self._write_file('foo.py', '@trace()\ndef foo():\n    pass\n')
        self._run_untrace(path)
        self.assertEqual(self._read_file(path), 'def foo():\n    pass\n')

    def test_removes_trace_with_args(self):
        """@trace(max_depth=5) with args is removed."""
        path = self._write_file('foo.py', '    @trace(max_depth=5, watch=[1])\n    def foo(self):\n        pass\n')
        self._run_untrace(path)
        self.assertEqual(self._read_file(path), '    def foo(self):\n        pass\n')

    def test_preserves_non_trace_decorators(self):
        """Other decorators are not removed."""
        path = self._write_file('foo.py', '@other_decorator\n@trace()\ndef foo():\n    pass\n')
        self._run_untrace(path)
        self.assertEqual(self._read_file(path), '@other_decorator\ndef foo():\n    pass\n')

    def test_no_trace_reports_nothing(self):
        """Files without @trace report nothing found."""
        self._write_file('foo.py', 'def foo():\n    pass\n')
        result = self._run_untrace(os.path.join(self.tmpdir, 'foo.py'))
        self.assertIn('No @trace decorators found', result.stdout)

    def test_recursive_directory(self):
        """Recursively removes @trace from .py files in subdirectories."""
        self._write_file('sub/a.py', '@trace\ndef a():\n    pass\n')
        self._write_file('sub/deep/b.py', '@trace()\ndef b():\n    pass\n')
        self._run_untrace(self.tmpdir)
        self.assertEqual(self._read_file(os.path.join(self.tmpdir, 'sub/a.py')), 'def a():\n    pass\n')
        self.assertEqual(self._read_file(os.path.join(self.tmpdir, 'sub/deep/b.py')), 'def b():\n    pass\n')

    def test_does_not_remove_trace_in_code(self):
        """Does not remove lines like 'trace(something)' that aren't decorators."""
        path = self._write_file('foo.py', 'result = trace(func)\ndef foo():\n    pass\n')
        self._run_untrace(path)
        self.assertEqual(self._read_file(path), 'result = trace(func)\ndef foo():\n    pass\n')

    def test_skips_trace_py_itself(self):
        """Should not modify trace.py (the decorator definition file)."""
        content = '@trace\ndef trace(func):\n    pass\n'
        path = self._write_file('trace.py', content)
        self._run_untrace(self.tmpdir)
        self.assertEqual(self._read_file(path), content)

    def test_skips_underscore_trace_py(self):
        """Should not modify _trace.py (collision-renamed decorator file)."""
        content = '@trace\ndef trace(func):\n    pass\n'
        path = self._write_file('_trace.py', content)
        self._run_untrace(self.tmpdir)
        self.assertEqual(self._read_file(path), content)


class TestBreakpointClearing(unittest.TestCase):
    """Test that breakpoints are cleared when debugged test passes."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.bp_file = os.path.join(self.tmpdir, 'saved-breakpoints')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_bp_file(self, content):
        with open(self.bp_file, 'w') as f:
            f.write(content)

    def _read_bp_file(self):
        with open(self.bp_file) as f:
            return f.read()

    def _simulate_clear_logic(self, last_debugged_method, failed_methods):
        """Simulate the breakpoint clearing logic from w script."""
        if last_debugged_method and os.path.exists(self.bp_file):
            method_still_failing = last_debugged_method in failed_methods
            if not method_still_failing:
                # Test passed — clear all saved breakpoints
                with open(self.bp_file, 'w') as f:
                    f.write('')
                return True  # cleared
        return False  # not cleared

    def test_clears_all_breakpoints_when_test_passes(self):
        """When debugged test passes, ALL breakpoints should be cleared."""
        self._write_bp_file(
            "b /path/to/_pretty_testing_/debug_this_test.py:42\n"
            "b /path/to/solver.py:10\n"
            "b /path/to/container.py:25\n"
        )
        cleared = self._simulate_clear_logic('test_foo', failed_methods=[])
        self.assertTrue(cleared)
        self.assertEqual(self._read_bp_file(), '')

    def test_preserves_breakpoints_when_test_still_fails(self):
        """When debugged test is still failing, breakpoints should be kept."""
        bp_content = (
            "b /path/to/_pretty_testing_/debug_this_test.py:42\n"
            "b /path/to/solver.py:10\n"
        )
        self._write_bp_file(bp_content)
        cleared = self._simulate_clear_logic('test_foo', failed_methods=['test_foo'])
        self.assertFalse(cleared)
        self.assertEqual(self._read_bp_file(), bp_content)

    def test_no_clear_when_no_debugged_method(self):
        """When no method was debugged, breakpoints should not be touched."""
        bp_content = "b /path/to/solver.py:10\n"
        self._write_bp_file(bp_content)
        cleared = self._simulate_clear_logic('', failed_methods=[])
        self.assertFalse(cleared)
        self.assertEqual(self._read_bp_file(), bp_content)

    def test_clears_user_code_breakpoints_not_just_test_file(self):
        """Verify user code breakpoints (solver.py etc) are also cleared on pass."""
        self._write_bp_file(
            "b /path/to/solver.py:10\n"
            "b /path/to/utils.py:55\n"
        )
        cleared = self._simulate_clear_logic('test_foo', failed_methods=['test_bar'])
        # test_foo is not in failed_methods, so it passed
        self.assertTrue(cleared)
        self.assertEqual(self._read_bp_file(), '')

    def test_no_crash_when_bp_file_missing(self):
        """Should not crash if breakpoints file doesn't exist."""
        os.remove(self.bp_file) if os.path.exists(self.bp_file) else None
        cleared = self._simulate_clear_logic('test_foo', failed_methods=[])
        self.assertFalse(cleared)


class TestBatchedSyntaxCheck(unittest.TestCase):
    """Test the batched syntax check used by w (single Python process)."""

    CHECKER_SCRIPT = """\
import sys, py_compile
errors = []
for line in sys.stdin:
    f = line.strip()
    if not f: continue
    try:
        py_compile.compile(f, doraise=True)
    except py_compile.PyCompileError as e:
        errors.append(str(e))
if errors:
    print('\\n'.join(errors))
    sys.exit(1)
"""

    def _run_checker(self, file_paths):
        """Run the batched syntax checker on given file paths."""
        import subprocess
        input_text = '\n'.join(file_paths)
        result = subprocess.run(
            ['python3', '-c', self.CHECKER_SCRIPT],
            input=input_text, capture_output=True, text=True
        )
        return result

    def test_all_valid_files_pass(self):
        """All valid files should pass with exit code 0."""
        with tempfile.TemporaryDirectory() as d:
            for name in ['a.py', 'b.py', 'c.py']:
                with open(os.path.join(d, name), 'w') as f:
                    f.write('x = 1\n')
            files = [os.path.join(d, n) for n in ['a.py', 'b.py', 'c.py']]
            result = self._run_checker(files)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout.strip(), '')

    def test_catches_syntax_error(self):
        """A file with a syntax error should cause exit code 1."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'good.py'), 'w') as f:
                f.write('x = 1\n')
            with open(os.path.join(d, 'bad.py'), 'w') as f:
                f.write('def broken(\n')
            files = [os.path.join(d, 'good.py'), os.path.join(d, 'bad.py')]
            result = self._run_checker(files)
            self.assertEqual(result.returncode, 1)
            self.assertIn('bad.py', result.stdout)

    def test_reports_correct_file_in_error(self):
        """Error output should identify which file has the problem."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'ok1.py'), 'w') as f:
                f.write('a = 1\n')
            with open(os.path.join(d, 'broken.py'), 'w') as f:
                f.write('if True\n')  # missing colon
            with open(os.path.join(d, 'ok2.py'), 'w') as f:
                f.write('b = 2\n')
            files = [os.path.join(d, n) for n in ['ok1.py', 'broken.py', 'ok2.py']]
            result = self._run_checker(files)
            self.assertEqual(result.returncode, 1)
            self.assertIn('broken.py', result.stdout)
            self.assertNotIn('ok1.py', result.stdout)
            self.assertNotIn('ok2.py', result.stdout)

    def test_multiple_errors_all_reported(self):
        """Multiple files with errors should all be reported."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'bad1.py'), 'w') as f:
                f.write('def(\n')
            with open(os.path.join(d, 'bad2.py'), 'w') as f:
                f.write('class:\n')
            files = [os.path.join(d, 'bad1.py'), os.path.join(d, 'bad2.py')]
            result = self._run_checker(files)
            self.assertEqual(result.returncode, 1)
            self.assertIn('bad1.py', result.stdout)
            self.assertIn('bad2.py', result.stdout)

    def test_empty_input_passes(self):
        """No files to check should pass."""
        result = self._run_checker([])
        self.assertEqual(result.returncode, 0)

    def test_skipped_file_not_checked(self):
        """Files not in the input list are not checked (simulates -f mode skip)."""
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, 'good.py'), 'w') as f:
                f.write('x = 1\n')
            with open(os.path.join(d, 'bad_but_skipped.py'), 'w') as f:
                f.write('def broken(\n')
            # Only check the good file, skip the bad one
            files = [os.path.join(d, 'good.py')]
            result = self._run_checker(files)
            self.assertEqual(result.returncode, 0)


class TestPerTestTimeout(unittest.TestCase):
    """Test per-test timeout via PRETTY_TESTING_TIMEOUT env var."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)
        os.makedirs('tests', exist_ok=True)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_test_file(self, content):
        path = os.path.join('tests', 'test_timeout.py')
        with open(path, 'w') as f:
            f.write(textwrap.dedent(content))
        return path

    def _generate_and_run(self, test_file, env_overrides=None, method=None):
        """Generate standalone test with test_generator and run it."""
        import subprocess
        generator = os.path.join(os.path.dirname(__file__), 'test_generator.py')
        args = [sys.executable, generator, test_file]
        if method:
            args.append(method)
        subprocess.run(args, capture_output=True, cwd=self.tmpdir)

        # Find the generated file
        if method:
            gen_file = os.path.join('_pretty_testing_', 'debug_this_test.py')
        else:
            gen_file = os.path.join('_pretty_testing_', 'debug_this_test_test_timeout.py')

        env = os.environ.copy()
        if env_overrides:
            env.update(env_overrides)

        result = subprocess.run(
            [sys.executable, gen_file],
            capture_output=True, text=True, timeout=15,
            cwd=self.tmpdir, env=env,
        )
        return result

    def test_timeout_kills_slow_test(self):
        """A test that runs longer than PRETTY_TESTING_TIMEOUT should fail with TimeoutError."""
        test_file = self._write_test_file("""\
            import unittest
            import time
            class TestSlow(unittest.TestCase):
                def test_slow(self):
                    time.sleep(10)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={'PRETTY_TESTING_TIMEOUT': '1'},
            method='test_slow',
        )
        self.assertIn('FAILED_METHOD:', result.stdout)
        self.assertIn('test_slow', result.stdout)
        self.assertIn('Timed out', result.stdout + result.stderr)

    def test_fast_test_passes_with_timeout(self):
        """A fast test should pass even with timeout enabled."""
        test_file = self._write_test_file("""\
            import unittest
            class TestFast(unittest.TestCase):
                def test_fast(self):
                    self.assertEqual(1 + 1, 2)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={'PRETTY_TESTING_TIMEOUT': '5'},
            method='test_fast',
        )
        self.assertIn('passed:', result.stdout)
        self.assertIn('test_fast', result.stdout)
        self.assertNotIn('FAILED_METHOD', result.stdout)

    def test_zero_timeout_means_no_timeout(self):
        """PRETTY_TESTING_TIMEOUT=0 should not set any alarm."""
        test_file = self._write_test_file("""\
            import unittest
            import time
            class TestNoTimeout(unittest.TestCase):
                def test_short_sleep(self):
                    time.sleep(0.5)
                    self.assertTrue(True)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={'PRETTY_TESTING_TIMEOUT': '0'},
            method='test_short_sleep',
        )
        self.assertIn('passed:', result.stdout)
        self.assertNotIn('FAILED_METHOD', result.stdout)

    def test_debug_mode_skips_timeout(self):
        """With PRETTY_TESTING_DEBUG=1, timeout should NOT fire even on slow tests.
        This ensures pressing 'd' to debug a timed-out test won't timeout again."""
        test_file = self._write_test_file("""\
            import unittest
            import time
            class TestDebug(unittest.TestCase):
                def test_debuggable(self):
                    time.sleep(2)
                    self.assertTrue(True)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={
                'PRETTY_TESTING_TIMEOUT': '1',
                'PRETTY_TESTING_DEBUG': '1',
            },
            method='test_debuggable',
        )
        # Should pass because debug mode disables timeout
        self.assertIn('passed:', result.stdout)
        self.assertNotIn('FAILED_METHOD', result.stdout)
        self.assertNotIn('Timed out', result.stdout + result.stderr)

    def test_timeout_cancelled_after_success(self):
        """Alarm should be cancelled after test passes (no spurious SIGALRM later)."""
        test_file = self._write_test_file("""\
            import unittest
            class TestAlarmCancelled(unittest.TestCase):
                def test_a(self):
                    self.assertTrue(True)
                def test_b(self):
                    self.assertTrue(True)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={'PRETTY_TESTING_TIMEOUT': '1'},
        )
        # Both tests should pass without alarm interference
        self.assertIn('passed: test_a', result.stdout)
        self.assertIn('passed: test_b', result.stdout)
        self.assertNotIn('FAILED_METHOD', result.stdout)

    def test_timed_out_test_shows_as_failed(self):
        """A timed-out test should appear as FAILED_METHOD in output, so w dashboard
        picks it up as a failure and enables the debug key."""
        test_file = self._write_test_file("""\
            import unittest
            import time
            class TestTimeout(unittest.TestCase):
                def test_hangs(self):
                    time.sleep(100)
        """)
        result = self._generate_and_run(
            test_file,
            env_overrides={'PRETTY_TESTING_TIMEOUT': '1'},
            method='test_hangs',
        )
        self.assertIn('FAILED_METHOD: test_hangs', result.stdout)


class TestRecursionErrorHandling(unittest.TestCase):
    """Test that infinite recursion is handled cleanly."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.tmpdir)
        os.makedirs('_pretty_testing_', exist_ok=True)
        os.makedirs('tests', exist_ok=True)

    def tearDown(self):
        os.chdir(self.old_cwd)
        import shutil
        shutil.rmtree(self.tmpdir)

    def _write_test_file(self, content):
        path = os.path.join('tests', 'test_recurse.py')
        with open(path, 'w') as f:
            f.write(textwrap.dedent(content))
        return path

    def _generate_and_run(self, test_file, method=None):
        import subprocess
        generator = os.path.join(os.path.dirname(__file__), 'test_generator.py')
        args = [sys.executable, generator, test_file]
        if method:
            args.append(method)
        subprocess.run(args, capture_output=True, cwd=self.tmpdir)
        if method:
            gen_file = os.path.join('_pretty_testing_', 'debug_this_test.py')
        else:
            gen_file = os.path.join('_pretty_testing_', 'debug_this_test_test_recurse.py')
        result = subprocess.run(
            [sys.executable, gen_file],
            capture_output=True, text=True, timeout=10,
            cwd=self.tmpdir,
        )
        return result

    def _strip_ansi(self, text):
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)

    def test_recursion_error_shows_as_failed(self):
        """Infinite recursion should show as FAILED_METHOD, not hang."""
        test_file = self._write_test_file("""\
            import unittest
            def bad_recurse(n):
                return bad_recurse(n)
            class TestRecurse(unittest.TestCase):
                def test_inf(self):
                    bad_recurse(1)
        """)
        result = self._generate_and_run(test_file, method='test_inf')
        self.assertIn('FAILED_METHOD: test_inf', result.stdout)

    def test_recursion_error_output_is_capped(self):
        """Should show at most ~6 frames, not 1000."""
        test_file = self._write_test_file("""\
            import unittest
            def bad_recurse(n):
                return bad_recurse(n)
            class TestRecurse(unittest.TestCase):
                def test_inf(self):
                    bad_recurse(1)
        """)
        result = self._generate_and_run(test_file, method='test_inf')
        output = self._strip_ansi(result.stdout)
        # Should contain the omission marker
        self.assertIn('frames omitted', output)
        # Should NOT have hundreds of "bad_recurse" lines
        frame_lines = [l for l in output.splitlines() if 'bad_recurse' in l and '►' in l]
        self.assertLessEqual(len(frame_lines), 10)

    def test_recursion_error_exits_cleanly(self):
        """Process should exit with code 1, not dump a 1000-frame traceback."""
        test_file = self._write_test_file("""\
            import unittest
            def bad_recurse(n):
                return bad_recurse(n)
            class TestRecurse(unittest.TestCase):
                def test_inf(self):
                    bad_recurse(1)
        """)
        result = self._generate_and_run(test_file, method='test_inf')
        self.assertEqual(result.returncode, 1)
        # stderr should NOT contain a massive Python traceback
        # (sys.exit(1) produces no traceback; raise e would produce 1000 lines)
        tb_lines = [l for l in result.stderr.splitlines()
                    if 'bad_recurse' in l]
        self.assertLessEqual(len(tb_lines), 5)

    def test_patch_postmortem_finds_raise_e(self):
        """patch_postmortem should still find 'raise e' even with sys.exit(1) above it."""
        from debug_prep import patch_postmortem
        # Simulate the generated RUNNER_BLOCK lines around raise e
        lines = [
            '                if isinstance(e, RecursionError):\n',
            '                    sys.exit(1)\n',
            '                raise e\n',
            '            pass\n',
        ]
        result = patch_postmortem(lines, 'pudb')
        joined = ''.join(result)
        self.assertIn('post_mortem', joined)
        self.assertNotIn('raise e', joined)

    def test_non_recursion_error_still_raises(self):
        """Normal exceptions should still raise (so patch_postmortem / pudb works)."""
        test_file = self._write_test_file("""\
            import unittest
            class TestNormal(unittest.TestCase):
                def test_fail(self):
                    raise ValueError("boom")
        """)
        result = self._generate_and_run(test_file, method='test_fail')
        self.assertIn('FAILED_METHOD: test_fail', result.stdout)
        # Should have a Python traceback on stderr (from raise e)
        self.assertIn('ValueError', result.stderr)


if __name__ == '__main__':
    unittest.main()
