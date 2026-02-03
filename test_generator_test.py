#!/usr/bin/env python3
"""Tests for test_generator.py — file discovery and generation."""
import os
import sys
import shutil
import subprocess
import tempfile
import textwrap
import unittest


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
GENERATOR = os.path.join(REPO_ROOT, 'test_generator.py')


class TestFileDiscovery(unittest.TestCase):
    """Verify test_generator.py handles arbitrary file names and structures."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.custom_dir = os.path.join(self.tmpdir, 'custom')
        os.makedirs(self.custom_dir)
        self.tests_dir = os.path.join(self.tmpdir, 'tests')
        os.makedirs(self.tests_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write_test_file(self, directory, filename, content):
        path = os.path.join(directory, filename)
        with open(path, 'w') as f:
            f.write(textwrap.dedent(content))
        return path

    def _run_generator(self, test_file, method=None):
        """Run test_generator.py and return (returncode, stdout, stderr)."""
        cmd = [sys.executable, GENERATOR, test_file]
        if method:
            cmd.append(method)
        return subprocess.run(
            cmd, capture_output=True, text=True, cwd=self.tmpdir
        )

    def _run_generated(self, filename):
        """Run a generated file and return (returncode, stdout, stderr)."""
        path = os.path.join(self.custom_dir, filename)
        return subprocess.run(
            [sys.executable, path], capture_output=True, text=True, cwd=self.tmpdir
        )

    # --- File naming tests ---

    def test_standard_test_filename(self):
        """test_foo.py — the normal case."""
        self._write_test_file(self.tests_dir, 'test_foo.py', """\
            import unittest
            class TestFoo(unittest.TestCase):
                def test_one(self):
                    self.assertEqual(1, 1)
        """)
        r = self._run_generator(os.path.join(self.tests_dir, 'test_foo.py'))
        self.assertEqual(r.returncode, 0)
        # Should produce custom/debug_this_test_test_foo.py
        self.assertTrue(os.path.exists(os.path.join(self.custom_dir, 'debug_this_test_test_foo.py')))

    def test_nonstandard_filename(self):
        """DemoICATest.py — no test_ prefix, CamelCase."""
        self._write_test_file(self.tests_dir, 'DemoICATest.py', """\
            import unittest
            class DemoICATest(unittest.TestCase):
                def test_one(self):
                    self.assertEqual(1, 1)
        """)
        r = self._run_generator(os.path.join(self.tests_dir, 'DemoICATest.py'))
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(os.path.join(self.custom_dir, 'debug_this_test_DemoICATest.py')))

    def test_filename_with_spaces_and_dashes(self):
        """my-test file.py — weird but legal filename."""
        self._write_test_file(self.tests_dir, 'my-test file.py', """\
            import unittest
            class TestWeird(unittest.TestCase):
                def test_one(self):
                    self.assertEqual(1, 1)
        """)
        r = self._run_generator(os.path.join(self.tests_dir, 'my-test file.py'))
        self.assertEqual(r.returncode, 0)

    # --- Generated file actually runs ---

    def test_generated_all_methods_runs(self):
        """Generated file with all methods produces pass/fail output."""
        self._write_test_file(self.tests_dir, 'check.py', """\
            import unittest
            class TestCheck(unittest.TestCase):
                def test_pass(self):
                    self.assertTrue(True)
                def test_fail(self):
                    self.assertEqual(1, 2)
        """)
        self._run_generator(os.path.join(self.tests_dir, 'check.py'))
        r = self._run_generated('debug_this_test_check.py')
        self.assertIn('passed: test_pass', r.stdout)
        self.assertIn('FAILED_METHOD: test_fail', r.stdout)

    def test_generated_single_method_runs(self):
        """Generated file with a single method produces output for just that method."""
        self._write_test_file(self.tests_dir, 'multi.py', """\
            import unittest
            class TestMulti(unittest.TestCase):
                def test_a(self):
                    self.assertTrue(True)
                def test_b(self):
                    self.assertTrue(True)
        """)
        self._run_generator(os.path.join(self.tests_dir, 'multi.py'), 'test_a')
        r = self._run_generated('debug_this_test.py')
        self.assertIn('passed: test_a', r.stdout)
        # test_b should not appear at all
        self.assertNotIn('test_b', r.stdout)

    # --- Class/method discovery ---

    def test_discovers_class_without_test_prefix(self):
        """Class named Container1Test (not TestContainer) is found."""
        self._write_test_file(self.tests_dir, 'stuff.py', """\
            import unittest
            class Container1Test(unittest.TestCase):
                def test_it(self):
                    self.assertTrue(True)
        """)
        self._run_generator(os.path.join(self.tests_dir, 'stuff.py'))
        r = self._run_generated('debug_this_test_stuff.py')
        self.assertIn('passed: test_it', r.stdout)

    def test_no_test_class_reports_not_found(self):
        """File with no TestCase subclass reports NO_TEST_CLASS_FOUND."""
        self._write_test_file(self.tests_dir, 'empty.py', """\
            x = 1
        """)
        self._run_generator(os.path.join(self.tests_dir, 'empty.py'))
        r = self._run_generated('debug_this_test_empty.py')
        self.assertIn('NO_TEST_CLASS_FOUND', r.stdout)

    def test_no_test_methods_reports_not_found(self):
        """TestCase with no test_ methods reports NO_TESTS_FOUND_IN_FILE."""
        self._write_test_file(self.tests_dir, 'nomethod.py', """\
            import unittest
            class TestEmpty(unittest.TestCase):
                def helper(self):
                    pass
        """)
        self._run_generator(os.path.join(self.tests_dir, 'nomethod.py'))
        r = self._run_generated('debug_this_test_nomethod.py')
        self.assertIn('NO_TESTS_FOUND_IN_FILE', r.stdout)


class TestUnittestPatterns(unittest.TestCase):
    """Edge cases from real-world unittest usage."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.custom_dir = os.path.join(self.tmpdir, 'custom')
        os.makedirs(self.custom_dir)
        self.tests_dir = os.path.join(self.tmpdir, 'tests')
        os.makedirs(self.tests_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _write(self, filename, content):
        path = os.path.join(self.tests_dir, filename)
        with open(path, 'w') as f:
            f.write(textwrap.dedent(content))
        return path

    def _gen(self, test_file, method=None):
        cmd = [sys.executable, GENERATOR, test_file]
        if method:
            cmd.append(method)
        return subprocess.run(cmd, capture_output=True, text=True, cwd=self.tmpdir)

    def _run(self, filename):
        path = os.path.join(self.custom_dir, filename)
        return subprocess.run(
            [sys.executable, path], capture_output=True, text=True, cwd=self.tmpdir
        )

    def test_multiple_testcase_classes(self):
        """All TestCase subclasses should be discovered and run."""
        self._write('multi_class.py', """\
            import unittest
            class ZTest(unittest.TestCase):
                def test_z(self):
                    self.assertTrue(True)
            class ATest(unittest.TestCase):
                def test_a(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'multi_class.py'))
        r = self._run('debug_this_test_multi_class.py')
        self.assertIn('passed: test_a', r.stdout)
        self.assertIn('passed: test_z', r.stdout)

    def test_inherited_test_class(self):
        """Both base and child classes run. Child inherits base's tests."""
        self._write('inherit.py', """\
            import unittest
            class BaseTest(unittest.TestCase):
                def test_base(self):
                    self.assertTrue(True)
            class ChildTest(BaseTest):
                def test_child(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'inherit.py'))
        r = self._run('debug_this_test_inherit.py')
        # BaseTest runs test_base
        # ChildTest runs test_base (inherited) AND test_child
        output = r.stdout
        self.assertEqual(output.count('passed: test_base'), 2)
        self.assertIn('passed: test_child', output)

    def test_setup_class(self):
        """Tests relying on setUpClass — runner should call it."""
        self._write('setup_cls.py', """\
            import unittest
            class TestWithSetupClass(unittest.TestCase):
                shared = None
                @classmethod
                def setUpClass(cls):
                    cls.shared = 42
                def test_uses_shared(self):
                    self.assertEqual(self.shared, 42)
        """)
        self._gen(os.path.join(self.tests_dir, 'setup_cls.py'))
        r = self._run('debug_this_test_setup_cls.py')
        self.assertIn('passed: test_uses_shared', r.stdout)

    def test_skip_decorator(self):
        """@unittest.skip — should be reported as skipped, not failed."""
        self._write('skipped.py', """\
            import unittest
            class TestSkip(unittest.TestCase):
                @unittest.skip("not ready")
                def test_skipped(self):
                    self.fail("should not run")
                def test_normal(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'skipped.py'))
        r = self._run('debug_this_test_skipped.py')
        self.assertIn('passed: test_normal', r.stdout)
        self.assertIn('skipped: test_skipped', r.stdout)
        self.assertNotIn('FAILED_METHOD: test_skipped', r.stdout)

    def test_expected_failure(self):
        """@unittest.expectedFailure — runner doesn't know about it."""
        self._write('expfail.py', """\
            import unittest
            class TestExpFail(unittest.TestCase):
                @unittest.expectedFailure
                def test_known_broken(self):
                    self.assertEqual(1, 2)
                def test_ok(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'expfail.py'))
        r = self._run('debug_this_test_expfail.py')
        self.assertIn('passed: test_ok', r.stdout)
        # expectedFailure wraps the method — it catches AssertionError internally
        # and raises _ExpectedFailure or returns success depending on version
        # Either way the runner sees it as passed or failed, not special
        self.assertIn('test_known_broken', r.stdout)

    def test_custom_failure_exception(self):
        """failureException = Exception — like the user's DemoICATest."""
        self._write('custom_exc.py', """\
            import unittest
            class TestCustomExc(unittest.TestCase):
                failureException = Exception
                def test_raises(self):
                    raise ValueError("boom")
                def test_ok(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'custom_exc.py'))
        r = self._run('debug_this_test_custom_exc.py')
        self.assertIn('FAILED_METHOD: test_raises', r.stdout)
        self.assertIn('passed: test_ok', r.stdout)

    def test_assert_raises_context_manager(self):
        """assertRaises used as context manager."""
        self._write('ctx_raises.py', """\
            import unittest
            class TestCtx(unittest.TestCase):
                def test_raises_cm(self):
                    with self.assertRaises(ValueError):
                        raise ValueError("expected")
                def test_raises_cm_fails(self):
                    with self.assertRaises(ValueError):
                        pass  # doesn't raise — should fail
        """)
        self._gen(os.path.join(self.tests_dir, 'ctx_raises.py'))
        r = self._run('debug_this_test_ctx_raises.py')
        self.assertIn('passed: test_raises_cm', r.stdout)
        self.assertIn('FAILED_METHOD: test_raises_cm_fails', r.stdout)

    def test_subtest(self):
        """subTest context manager — failures inside subTest still propagate."""
        self._write('subtest.py', """\
            import unittest
            class TestSub(unittest.TestCase):
                def test_with_subtests(self):
                    for i in range(3):
                        with self.subTest(i=i):
                            self.assertNotEqual(i, 1)
        """)
        self._gen(os.path.join(self.tests_dir, 'subtest.py'))
        r = self._run('debug_this_test_subtest.py')
        # subTest catches failures internally and re-raises at the end
        # The runner should see this as a failure
        self.assertIn('test_with_subtests', r.stdout)

    def test_no_setup_method(self):
        """TestCase with no setUp — should work fine."""
        self._write('no_setup.py', """\
            import unittest
            class TestNoSetup(unittest.TestCase):
                def test_simple(self):
                    self.assertEqual(2 + 2, 4)
        """)
        self._gen(os.path.join(self.tests_dir, 'no_setup.py'))
        r = self._run('debug_this_test_no_setup.py')
        self.assertIn('passed: test_simple', r.stdout)

    def test_teardown_called(self):
        """tearDown is called even after failure."""
        self._write('teardown.py', """\
            import unittest
            class TestTeardown(unittest.TestCase):
                cleaned = False
                def tearDown(self):
                    TestTeardown.cleaned = True
                def test_fail(self):
                    self.assertEqual(1, 2)
        """)
        self._gen(os.path.join(self.tests_dir, 'teardown.py'))
        r = self._run('debug_this_test_teardown.py')
        self.assertIn('FAILED_METHOD: test_fail', r.stdout)
        # Can't easily check tearDown was called from outside,
        # but we verify it doesn't crash

    def test_setup_class_failure_skips_all_methods(self):
        """If setUpClass fails, all methods in that class should fail."""
        self._write('setup_cls_fail.py', """\
            import unittest
            class TestBrokenSetup(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    raise RuntimeError("class setup boom")
                def test_a(self):
                    pass
                def test_b(self):
                    pass
        """)
        self._gen(os.path.join(self.tests_dir, 'setup_cls_fail.py'))
        r = self._run('debug_this_test_setup_cls_fail.py')
        self.assertIn('FAILED_METHOD: test_a', r.stdout)
        self.assertIn('FAILED_METHOD: test_b', r.stdout)
        self.assertIn('setUpClass failed', r.stdout)

    def test_teardown_class_called(self):
        """tearDownClass is called after all tests in a class."""
        self._write('td_cls.py', """\
            import unittest
            _log = []
            class TestTDClass(unittest.TestCase):
                @classmethod
                def setUpClass(cls):
                    _log.append('setup')
                @classmethod
                def tearDownClass(cls):
                    _log.append('teardown')
                    # Print so we can verify from outside
                    print("TEARDOWN_CLASS_CALLED")
                def test_one(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'td_cls.py'))
        r = self._run('debug_this_test_td_cls.py')
        self.assertIn('passed: test_one', r.stdout)
        self.assertIn('TEARDOWN_CLASS_CALLED', r.stdout)

    def test_setup_module(self):
        """setUpModule is called before any tests."""
        self._write('setup_mod.py', """\
            import unittest
            _shared = {}
            def setUpModule():
                _shared['ready'] = True
            class TestMod(unittest.TestCase):
                def test_module_ready(self):
                    self.assertTrue(_shared.get('ready'))
        """)
        self._gen(os.path.join(self.tests_dir, 'setup_mod.py'))
        r = self._run('debug_this_test_setup_mod.py')
        self.assertIn('passed: test_module_ready', r.stdout)

    def test_setup_module_failure(self):
        """If setUpModule fails, all tests should fail."""
        self._write('setup_mod_fail.py', """\
            import unittest
            def setUpModule():
                raise RuntimeError("module boom")
            class TestMod(unittest.TestCase):
                def test_a(self):
                    pass
        """)
        self._gen(os.path.join(self.tests_dir, 'setup_mod_fail.py'))
        r = self._run('debug_this_test_setup_mod_fail.py')
        self.assertIn('FAILED_METHOD: test_a', r.stdout)
        self.assertIn('setUpModule failed', r.stdout)

    def test_skip_if_condition(self):
        """@unittest.skipIf — conditional skip."""
        self._write('skipif.py', """\
            import unittest
            class TestSkipIf(unittest.TestCase):
                @unittest.skipIf(True, "always skip")
                def test_conditional_skip(self):
                    self.fail("should not run")
                @unittest.skipIf(False, "never skip")
                def test_conditional_run(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'skipif.py'))
        r = self._run('debug_this_test_skipif.py')
        self.assertIn('skipped: test_conditional_skip', r.stdout)
        self.assertIn('passed: test_conditional_run', r.stdout)

    def test_single_method_from_correct_class(self):
        """When targeting a method, find it in the right class even if not first."""
        self._write('two_classes.py', """\
            import unittest
            class AlphaTest(unittest.TestCase):
                def test_alpha(self):
                    self.assertTrue(True)
            class BetaTest(unittest.TestCase):
                def test_beta(self):
                    self.assertTrue(True)
        """)
        self._gen(os.path.join(self.tests_dir, 'two_classes.py'), 'test_beta')
        r = self._run('debug_this_test.py')
        self.assertIn('passed: test_beta', r.stdout)
        self.assertNotIn('test_alpha', r.stdout)

    def test_expected_failure_pass(self):
        """@expectedFailure — test that fails as expected should pass."""
        self._write('expfail2.py', """\
            import unittest
            class TestExpFail(unittest.TestCase):
                @unittest.expectedFailure
                def test_known_broken(self):
                    self.assertEqual(1, 2)
        """)
        self._gen(os.path.join(self.tests_dir, 'expfail2.py'))
        r = self._run('debug_this_test_expfail2.py')
        # expectedFailure catches the assertion internally — should pass
        self.assertIn('passed: test_known_broken', r.stdout)


class TestWatchFileGeneration(unittest.TestCase):
    """Test that watch_*.py files are generated correctly for w script."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.custom_dir = os.path.join(self.tmpdir, 'custom')
        os.makedirs(self.custom_dir)
        self.tests_dir = os.path.join(self.tmpdir, 'tests')
        os.makedirs(self.tests_dir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def _create_watch_generator(self):
        """Create the watch version of test_generator (as w script does)."""
        generator_path = os.path.join(REPO_ROOT, 'test_generator.py')
        with open(generator_path) as f:
            content = f.read()
        # Apply same transformations as w script
        content = content.replace('debug_this_test_', 'watch_')
        content = content.replace('debug_this_test.py', 'watch_.py')
        content = content.replace('raise e', 'pass')
        watch_gen_path = os.path.join(self.custom_dir, 'make_watch_test.py')
        with open(watch_gen_path, 'w') as f:
            f.write(content)
        return watch_gen_path

    def test_watch_generator_produces_watch_files(self):
        """Verify watch generator creates watch_*.py files that run."""
        # Create a test file
        test_path = os.path.join(self.tests_dir, 'test_example.py')
        with open(test_path, 'w') as f:
            f.write(textwrap.dedent("""\
                import unittest
                class TestExample(unittest.TestCase):
                    def test_one(self):
                        self.assertEqual(1, 1)
                    def test_two(self):
                        self.assertEqual(2, 2)
            """))

        watch_gen = self._create_watch_generator()

        # Run the watch generator
        r = subprocess.run(
            [sys.executable, watch_gen, test_path],
            capture_output=True, text=True, cwd=self.tmpdir
        )

        # Should produce watch_test_example.py
        watch_file = os.path.join(self.custom_dir, 'watch_test_example.py')
        self.assertTrue(os.path.exists(watch_file),
                        f"Expected {watch_file} to exist. Generator output: {r.stdout} {r.stderr}")

        # Run the watch file and verify it produces output
        r2 = subprocess.run(
            [sys.executable, watch_file],
            capture_output=True, text=True, cwd=self.tmpdir
        )
        self.assertIn('passed: test_one', r2.stdout)
        self.assertIn('passed: test_two', r2.stdout)

    def test_watch_generator_weird_filename(self):
        """Verify watch generator handles non-standard filenames."""
        # Create a test file with weird name (no test_ prefix, CamelCase)
        test_path = os.path.join(self.tests_dir, 'MyWeirdTest.py')
        with open(test_path, 'w') as f:
            f.write(textwrap.dedent("""\
                import unittest
                class MyWeirdTest(unittest.TestCase):
                    def test_works(self):
                        self.assertTrue(True)
            """))

        watch_gen = self._create_watch_generator()

        # Run the watch generator
        r = subprocess.run(
            [sys.executable, watch_gen, test_path],
            capture_output=True, text=True, cwd=self.tmpdir
        )

        # Should produce watch_MyWeirdTest.py
        watch_file = os.path.join(self.custom_dir, 'watch_MyWeirdTest.py')
        self.assertTrue(os.path.exists(watch_file),
                        f"Expected {watch_file} to exist. Generator output: {r.stdout} {r.stderr}")

        # Run and verify
        r2 = subprocess.run(
            [sys.executable, watch_file],
            capture_output=True, text=True, cwd=self.tmpdir
        )
        self.assertIn('passed: test_works', r2.stdout)


if __name__ == '__main__':
    unittest.main()
