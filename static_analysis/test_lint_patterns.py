#!/usr/bin/env python3
"""
Test suite for lint_patterns.py
===============================
Verifies that the linting patterns catch the expected issues
and don't produce too many false positives.
"""

import unittest
from pathlib import Path
from lint_patterns import (
    scan_file,
    check_regex_patterns,
    check_ast_patterns,
    LintIssue,
)


class TestRegexPatterns(unittest.TestCase):
    """Test regex-based pattern detection."""

    def check_pattern(self, code: str, expected_rule_id: str, should_match: bool = True):
        """Helper to check if a pattern matches code."""
        issues = check_regex_patterns(code, "test.py")
        rule_ids = [issue.rule_id for issue in issues]

        if should_match:
            self.assertIn(
                expected_rule_id, rule_ids,
                f"Expected rule '{expected_rule_id}' to match:\n{code}\nGot: {rule_ids}"
            )
        else:
            self.assertNotIn(
                expected_rule_id, rule_ids,
                f"Expected rule '{expected_rule_id}' NOT to match:\n{code}\nGot: {rule_ids}"
            )

    # NaN comparison tests
    def test_nan_equality_np(self):
        """Should catch == np.nan"""
        self.check_pattern("if x == np.nan:", "nan_equality", True)

    def test_nan_equality_float(self):
        """Should catch == float('nan')"""
        self.check_pattern("if x == float('nan'):", "nan_equality", True)

    def test_nan_equality_math(self):
        """Should catch == math.nan"""
        self.check_pattern("if x == math.nan:", "nan_equality", True)

    def test_nan_inequality(self):
        """Should catch != np.nan"""
        self.check_pattern("if x != np.nan:", "nan_inequality", True)

    def test_isnan_ok(self):
        """Should NOT flag np.isnan()"""
        self.check_pattern("if np.isnan(x):", "nan_equality", False)

    # _replace discarded tests
    def test_replace_discarded(self):
        """Should catch _replace without assignment"""
        self.check_pattern("    point._replace(x=10)", "replace_discarded", True)

    def test_replace_assigned_ok(self):
        """Should NOT flag _replace when assigned"""
        self.check_pattern("    new_point = point._replace(x=10)", "replace_discarded", False)

    # shuffle assigned tests
    def test_shuffle_assigned(self):
        """Should catch shuffle() result being assigned"""
        self.check_pattern("result = rng.shuffle(arr)", "shuffle_assigned", True)
        self.check_pattern("x = np.random.shuffle(arr)", "shuffle_assigned", True)

    def test_shuffle_standalone_ok(self):
        """Should NOT flag shuffle() when not assigned"""
        self.check_pattern("rng.shuffle(arr)", "shuffle_assigned", False)

    # Global random tests
    def test_global_random(self):
        """Should catch global np.random.* calls"""
        self.check_pattern("x = np.random.random(5)", "global_random", True)
        self.check_pattern("x = np.random.randn(3, 4)", "global_random", True)
        self.check_pattern("x = np.random.normal(0, 1)", "global_random", True)

    def test_global_random_ok(self):
        """Should NOT flag RandomState/default_rng/seed"""
        self.check_pattern("rng = np.random.RandomState(42)", "global_random", False)
        self.check_pattern("rng = np.random.default_rng(42)", "global_random", False)
        self.check_pattern("np.random.seed(42)", "global_random", False)

    # Float equality tests
    def test_float_equality(self):
        """Should catch float equality comparisons"""
        self.check_pattern("if result == 0.3:", "float_equality", True)
        self.check_pattern("if x == 3.14159:", "float_equality", True)

    def test_int_equality_ok(self):
        """Should NOT flag integer comparisons"""
        self.check_pattern("if x == 3:", "float_equality", False)

    # where/nonzero not indexed tests
    def test_where_not_indexed(self):
        """Should catch np.where() result being discarded (bare expression)"""
        # Only flag when result is not assigned - bare expression is definitely a bug
        self.check_pattern("    np.where(arr > 0)", "where_nonzero_not_indexed", True)
        self.check_pattern("    np.nonzero(arr > 0)", "where_nonzero_not_indexed", True)

    def test_where_assigned_ok(self):
        """Should NOT flag np.where when assigned (user may index later)"""
        self.check_pattern("result = np.where(arr > 0)", "where_nonzero_not_indexed", False)
        self.check_pattern("o = np.nonzero(arr > 0)", "where_nonzero_not_indexed", False)

    def test_where_indexed_ok(self):
        """Should NOT flag np.where when properly used"""
        self.check_pattern("arr[np.where(arr > 0)]", "where_nonzero_not_indexed", False)

    def test_where_3arg_ok(self):
        """Should NOT flag 3-arg np.where"""
        self.check_pattern("np.where(arr > 0, arr, 0)", "where_nonzero_not_indexed", False)

    # Python min/max with arrays
    def test_python_min_arrays(self):
        """Should flag Python min() with two array-like args"""
        self.check_pattern("result = min(arr1, arr2)", "python_min_max_arrays", True)

    def test_np_minimum_ok(self):
        """Should NOT flag np.minimum()"""
        self.check_pattern("result = np.minimum(arr1, arr2)", "python_min_max_arrays", False)

    # rng.random wrong shape
    def test_random_wrong_shape(self):
        """Should catch rng.random(3, 4) instead of rng.random((3, 4))"""
        self.check_pattern("x = rng.random(3, 4)", "random_wrong_shape", True)

    def test_random_tuple_ok(self):
        """Should NOT flag rng.random((3, 4))"""
        self.check_pattern("x = rng.random((3, 4))", "random_wrong_shape", False)

    # Walrus in comprehension
    def test_walrus_in_comprehension(self):
        """Should flag walrus operator in list comprehension"""
        self.check_pattern("[((x := x + 1), y)[1] for y in items]", "walrus_in_comprehension", True)

    # sort() assigned tests
    def test_sort_assigned(self):
        """Should catch sort() result being assigned"""
        self.check_pattern("result = mylist.sort()", "sort_assigned", True)
        self.check_pattern("x = items.sort(key=len)", "sort_assigned", True)

    def test_sort_standalone_ok(self):
        """Should NOT flag sort() when not assigned"""
        self.check_pattern("mylist.sort()", "sort_assigned", False)

    def test_sorted_ok(self):
        """Should NOT flag sorted() which returns a value"""
        self.check_pattern("result = sorted(mylist)", "sort_assigned", False)

    def test_np_sort_ok(self):
        """Should NOT flag np.sort() which returns a value"""
        self.check_pattern("result = np.sort(arr)", "sort_assigned", False)
        self.check_pattern("sorted_arr = np.sort(arr, axis=-1)", "sort_assigned", False)

    # reverse() assigned tests
    def test_reverse_assigned(self):
        """Should catch reverse() result being assigned"""
        self.check_pattern("result = mylist.reverse()", "reverse_assigned", True)

    def test_reverse_standalone_ok(self):
        """Should NOT flag reverse() when not assigned"""
        self.check_pattern("mylist.reverse()", "reverse_assigned", False)

    def test_reversed_ok(self):
        """Should NOT flag reversed() which returns a value"""
        self.check_pattern("result = reversed(mylist)", "reverse_assigned", False)

    # np.append discarded tests
    def test_np_append_discarded(self):
        """Should catch np.append() result not being assigned"""
        self.check_pattern("    np.append(arr, 5)", "np_append_discarded", True)
        self.check_pattern("    np.append(arr, 5)  # comment", "np_append_discarded", True)

    def test_np_append_assigned_ok(self):
        """Should NOT flag np.append() when assigned"""
        self.check_pattern("    arr = np.append(arr, 5)", "np_append_discarded", False)


class TestASTPatterns(unittest.TestCase):
    """Test AST-based pattern detection."""

    def check_ast_pattern(self, code: str, expected_rule_id: str, should_match: bool = True):
        """Helper to check if an AST pattern matches code."""
        issues = check_ast_patterns(code, "test.py")
        rule_ids = [issue.rule_id for issue in issues]

        if should_match:
            self.assertIn(
                expected_rule_id, rule_ids,
                f"Expected rule '{expected_rule_id}' to match:\n{code}\nGot: {rule_ids}"
            )
        else:
            self.assertNotIn(
                expected_rule_id, rule_ids,
                f"Expected rule '{expected_rule_id}' NOT to match:\n{code}\nGot: {rule_ids}"
            )

    # Recursion not returned
    def test_recursion_not_returned(self):
        """Should catch recursive call without return"""
        code = """
def find_max(lst, idx=0, current_max=None):
    if idx >= len(lst):
        return current_max
    find_max(lst, idx + 1, current_max)
"""
        self.check_ast_pattern(code, "recursion_not_returned", True)

    def test_recursion_returned_ok(self):
        """Should NOT flag recursive call with return"""
        code = """
def find_max(lst, idx=0, current_max=None):
    if idx >= len(lst):
        return current_max
    return find_max(lst, idx + 1, current_max)
"""
        self.check_ast_pattern(code, "recursion_not_returned", False)

    # Recursion unchanged argument
    def test_recursion_unchanged_arg(self):
        """Should catch recursive call with unchanged first argument"""
        code = """
def sum_to_n(n):
    if n <= 0:
        return 0
    return n + sum_to_n(n)
"""
        self.check_ast_pattern(code, "recursion_unchanged_arg", True)

    def test_recursion_changed_arg_ok(self):
        """Should NOT flag recursive call with changed argument"""
        code = """
def sum_to_n(n):
    if n <= 0:
        return 0
    return n + sum_to_n(n - 1)
"""
        self.check_ast_pattern(code, "recursion_unchanged_arg", False)

    # Comprehension shadowing
    def test_comprehension_shadowing(self):
        """Should catch variable shadowing in nested comprehension"""
        code = "[[x for x in row] for x in matrix]"
        self.check_ast_pattern(code, "comprehension_shadowing", True)

    def test_comprehension_distinct_vars_ok(self):
        """Should NOT flag distinct variable names"""
        code = "[[cell for cell in row] for row in matrix]"
        self.check_ast_pattern(code, "comprehension_shadowing", False)

    # NamedTuple positional
    def test_namedtuple_positional(self):
        """Should flag NamedTuple-like instantiation with positional args"""
        code = "p = Point(10, 20)"
        self.check_ast_pattern(code, "namedtuple_positional", True)

    def test_namedtuple_keyword_ok(self):
        """Should NOT flag NamedTuple with keyword args"""
        code = "p = Point(x=10, y=20)"
        self.check_ast_pattern(code, "namedtuple_positional", False)

    # Reduction without keepdims in binop
    def test_reduction_no_keepdims(self):
        """Should flag reduction with axis in binary op without keepdims"""
        code = "result = arr - np.mean(arr, axis=1)"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_no_keepdims_positional_axis(self):
        """Should flag reduction with positional axis arg"""
        code = "result = arr - np.sum(arr, 1)"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_with_keepdims_ok(self):
        """Should NOT flag reduction with keepdims=True"""
        code = "result = arr - np.mean(arr, axis=1, keepdims=True)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_subscripted_ok(self):
        """Should NOT flag reduction that is subscripted (dimension restored)"""
        # This pattern is arr - np.mean(arr, axis=1)[:, None]
        # The subscript restores dimensions, so it's valid
        code = "result = arr - np.mean(arr, axis=1)[:, None]"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_no_axis_ok(self):
        """Should NOT flag reduction without axis (reduces all)"""
        code = "result = arr - np.mean(arr)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_assignment_only_ok(self):
        """Should NOT flag reduction in simple assignment (not binop)"""
        code = "mean = np.mean(arr, axis=1)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_axis_0_ok(self):
        """Should NOT flag axis=0 (common correct pattern for feature normalization)"""
        code = "result = arr - np.mean(arr, axis=0)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_method_style(self):
        """Should flag method-style reduction without keepdims"""
        code = "result = x - x.mean(axis=1)"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_method_style_axis_0_ok(self):
        """Should NOT flag method-style with axis=0"""
        code = "result = x - x.mean(axis=0)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_method_style_keepdims_ok(self):
        """Should NOT flag method-style with keepdims"""
        code = "result = x - x.mean(axis=1, keepdims=True)"
        self.check_ast_pattern(code, "reduction_no_keepdims", False)

    def test_reduction_in_np_multiply(self):
        """Should flag reduction in np.multiply"""
        code = "result = np.multiply(x, np.sum(x, axis=1))"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_in_np_divide(self):
        """Should flag reduction in np.divide"""
        code = "result = np.divide(x, np.max(x, axis=1))"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_in_np_where_condition(self):
        """Should flag reduction in np.where condition comparison"""
        code = "result = np.where(x > np.mean(x, axis=1), x, 0)"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)

    def test_reduction_in_np_where_value(self):
        """Should flag reduction in np.where value"""
        code = "result = np.where(mask, x - np.mean(x, axis=1), 0)"
        self.check_ast_pattern(code, "reduction_no_keepdims", True)


class TestExampleFiles(unittest.TestCase):
    """Test that example files are properly analyzed."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(__file__).parent

    def test_floating_point_file(self):
        """Test that floating point file catches NaN comparisons."""
        filepath = self.test_dir / "04_floating_point.py"
        if not filepath.exists():
            self.skipTest(f"File {filepath} not found")

        issues = scan_file(filepath)
        rule_ids = [issue.rule_id for issue in issues]

        # Should catch NaN equality
        self.assertIn("nan_equality", rule_ids,
                      f"Should catch NaN equality in floating point file. Got: {rule_ids}")

    def test_namedtuple_file(self):
        """Test that namedtuple file catches _replace discarded."""
        filepath = self.test_dir / "03_namedtuple.py"
        if not filepath.exists():
            self.skipTest(f"File {filepath} not found")

        issues = scan_file(filepath)
        rule_ids = [issue.rule_id for issue in issues]

        # Should catch discarded _replace
        self.assertIn("replace_discarded", rule_ids,
                      f"Should catch _replace discarded in namedtuple file. Got: {rule_ids}")

    def test_recursion_file(self):
        """Test that recursion file catches recursion issues."""
        filepath = self.test_dir / "02_recursion.py"
        if not filepath.exists():
            self.skipTest(f"File {filepath} not found")

        issues = scan_file(filepath)
        rule_ids = [issue.rule_id for issue in issues]

        # Should catch at least one recursion issue
        recursion_issues = [r for r in rule_ids if r.startswith("recursion")]
        self.assertTrue(len(recursion_issues) > 0,
                        f"Should catch recursion issues. Got: {rule_ids}")

    def test_random_state_file(self):
        """Test that random state file catches global random calls."""
        filepath = self.test_dir / "11_random_state.py"
        if not filepath.exists():
            self.skipTest(f"File {filepath} not found")

        issues = scan_file(filepath)
        rule_ids = [issue.rule_id for issue in issues]

        # Should catch global random calls
        self.assertIn("global_random", rule_ids,
                      f"Should catch global random in random state file. Got: {rule_ids}")

    def test_list_comprehensions_file(self):
        """Test that list comprehensions file catches shadowing and walrus."""
        filepath = self.test_dir / "01_list_comprehensions.py"
        if not filepath.exists():
            self.skipTest(f"File {filepath} not found")

        issues = scan_file(filepath)
        rule_ids = [issue.rule_id for issue in issues]

        # Should catch comprehension shadowing
        self.assertIn("comprehension_shadowing", rule_ids,
                      f"Should catch comprehension shadowing. Got: {rule_ids}")


class TestNoFalsePositivesInGoodCode(unittest.TestCase):
    """Test that good patterns are NOT flagged."""

    def test_good_float_comparison(self):
        """Good float comparison should not be flagged."""
        code = """
import math
import numpy as np

def compare_floats():
    result = 0.1 + 0.2
    return math.isclose(result, 0.3)

def compare_arrays():
    a = np.array([0.1, 0.2])
    b = np.array([0.1, 0.2])
    return np.allclose(a, b)

def check_nan():
    return np.isnan(x)
"""
        issues = check_regex_patterns(code, "test.py")
        issues.extend(check_ast_patterns(code, "test.py"))

        # Should have no errors
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertEqual(len(errors), 0,
                         f"Good float code should have no errors. Got: {[i.rule_id for i in errors]}")

    def test_good_recursion(self):
        """Good recursion should not be flagged."""
        code = """
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial(n - 1)

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
"""
        issues = check_ast_patterns(code, "test.py")

        # Should have no recursion errors
        recursion_errors = [i for i in issues if i.rule_id.startswith("recursion")]
        self.assertEqual(len(recursion_errors), 0,
                         f"Good recursion should have no errors. Got: {[i.rule_id for i in recursion_errors]}")

    def test_good_namedtuple_usage(self):
        """Good namedtuple usage should not be flagged."""
        code = """
from collections import namedtuple

Point = namedtuple('Point', ['x', 'y'])

def create_point():
    return Point(x=10, y=20)

def update_point(p):
    return p._replace(x=100)
"""
        issues = check_regex_patterns(code, "test.py")
        issues.extend(check_ast_patterns(code, "test.py"))

        # Should have no namedtuple errors
        namedtuple_issues = [i for i in issues
                            if i.rule_id in ("replace_discarded", "namedtuple_positional")]
        # The positional check is INFO level, so we mainly care about replace_discarded
        replace_issues = [i for i in issues if i.rule_id == "replace_discarded"]
        self.assertEqual(len(replace_issues), 0,
                         f"Good namedtuple usage should not flag _replace. Got: {[i.rule_id for i in replace_issues]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
