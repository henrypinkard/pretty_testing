#!/usr/bin/env python3
"""
Static Detection of Python Error Patterns
==========================================
Regex patterns and AST-based checks to detect common Python/NumPy pitfalls.

Usage:
    python lint_patterns.py <file_or_directory>
    python lint_patterns.py .  # Scan current directory
"""

import ast
import re
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Set

try:
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import Terminal256Formatter
    PYGMENTS_AVAILABLE = True
except ImportError:
    PYGMENTS_AVAILABLE = False


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class LintIssue:
    """Represents a detected issue."""
    file: str
    line: int
    column: int
    rule_id: str
    severity: str  # ERROR, WARNING, INFO
    message: str
    code_snippet: Optional[str] = None


# =============================================================================
# Regex-based Patterns
# =============================================================================

REGEX_PATTERNS = {
    # HIGH CONFIDENCE
    "nan_equality": {
        "pattern": r"==\s*(?:np\.nan\b|float\s*\(\s*['\"]nan['\"]\s*\)|math\.nan\b)",
        "message": "== NaN is always False",
        "severity": "ERROR"
    },
    "nan_inequality": {
        "pattern": r"!=\s*(?:np\.nan\b|float\s*\(\s*['\"]nan['\"]\s*\)|math\.nan\b)",
        "message": "!= NaN is always True",
        "severity": "ERROR"
    },
    "replace_discarded": {
        "pattern": r"^\s+\w+\._replace\s*\([^)]*\)\s*(?:#.*)?$",
        "message": "_replace() result discarded",
        "severity": "WARNING"
    },
    "shuffle_assigned": {
        "pattern": r"\w+\s*=\s*\S*\.?shuffle\s*\(",
        "message": "shuffle() returns None",
        "severity": "ERROR"
    },
    "global_random": {
        "pattern": r"np\.random\.(?!RandomState|default_rng|seed|Generator|choice\()\w+\s*\(",
        "message": "global np.random state",
        "severity": "WARNING"
    },
    # MEDIUM CONFIDENCE
    "float_equality": {
        "pattern": r"==\s*\d+\.\d+(?!\d)",
        "message": "float equality",
        "severity": "WARNING"
    },
    "where_nonzero_not_indexed": {
        # Only flag when result is not assigned (bare expression) - if assigned, user may index later
        "pattern": r"^\s+np\.(where|nonzero)\s*\(\s*[^,)]+\s*\)\s*(?:#.*)?$",
        "message": "returns tuple of arrays, not array - use [0] for 1D or unpack for 2D",
        "severity": "WARNING"
    },
    "python_min_max_arrays": {
        "pattern": r"\b(?<!np\.)(min|max)\s*\(\s*\w+\s*,\s*\w+\s*\)",
        "message": "python min/max, not np.minimum/maximum",
        "severity": "INFO"
    },
    "random_wrong_shape": {
        "pattern": r"\.random\s*\(\s*\d+\s*,\s*\d+\s*[,)]",
        "message": "random() takes tuple: random((3,4))",
        "severity": "WARNING"
    },
    "walrus_in_comprehension": {
        "pattern": r"\[[^\]]*:=[^\]]*\]",
        "message": "walrus in comprehension",
        "severity": "INFO"
    },
    # In-place methods that return None (exclude np.sort which returns a value)
    "sort_assigned": {
        "pattern": r"\w+\s*=\s*\S*(?<!np)\.sort\s*\(",
        "message": "sort() returns None",
        "severity": "ERROR"
    },
    "reverse_assigned": {
        "pattern": r"\w+\s*=\s*\S*\.reverse\s*\(",
        "message": "reverse() returns None",
        "severity": "ERROR"
    },
    # np.append result discarded
    "np_append_discarded": {
        "pattern": r"^\s+np\.append\s*\([^)]*\)\s*(?:#.*)?$",
        "message": "np.append() result discarded",
        "severity": "WARNING"
    },
}


def check_regex_patterns(content: str, filename: str) -> List[LintIssue]:
    """Run all regex-based pattern checks on file content."""
    issues = []
    lines = content.split('\n')

    for line_num, line in enumerate(lines, start=1):
        # Skip comments and docstrings (simple heuristic)
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
            continue

        for rule_id, rule in REGEX_PATTERNS.items():
            pattern = rule["pattern"]
            for match in re.finditer(pattern, line):
                issues.append(LintIssue(
                    file=filename,
                    line=line_num,
                    column=match.start() + 1,
                    rule_id=rule_id,
                    severity=rule["severity"],
                    message=rule["message"],
                    code_snippet=line.strip()
                ))

    return issues


# =============================================================================
# AST-based Checks
# =============================================================================

class ASTChecker(ast.NodeVisitor):
    """AST visitor that checks for various error patterns."""

    def __init__(self, filename: str, source_lines: List[str]):
        self.filename = filename
        self.source_lines = source_lines
        self.issues: List[LintIssue] = []
        self.current_function: Optional[ast.FunctionDef] = None
        self.function_stack: List[ast.FunctionDef] = []

    def _add_issue(self, node: ast.AST, rule_id: str, severity: str, message: str):
        """Add an issue for a given AST node."""
        line = getattr(node, 'lineno', 0)
        col = getattr(node, 'col_offset', 0)
        snippet = self.source_lines[line - 1].strip() if line > 0 and line <= len(self.source_lines) else None

        self.issues.append(LintIssue(
            file=self.filename,
            line=line,
            column=col + 1,
            rule_id=rule_id,
            severity=severity,
            message=message,
            code_snippet=snippet
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Check function definitions for issues."""
        self.function_stack.append(node)
        old_function = self.current_function
        self.current_function = node

        # Check for recursion issues
        self._check_recursion_issues(node)

        self.generic_visit(node)

        self.current_function = old_function
        self.function_stack.pop()

    visit_AsyncFunctionDef = visit_FunctionDef

    def _check_recursion_issues(self, node: ast.FunctionDef):
        """Check for common recursion bugs."""
        func_name = node.name

        # Look for recursive calls in the function body
        for stmt in node.body:
            self._check_recursion_in_statement(stmt, func_name, node)

    def _check_recursion_in_statement(self, stmt: ast.stmt, func_name: str, func_node: ast.FunctionDef):
        """Recursively check a statement for recursion issues."""
        # Check if this is an Expr statement containing a recursive call
        if isinstance(stmt, ast.Expr):
            if self._is_recursive_call(stmt.value, func_name):
                self._add_issue(
                    stmt.value,
                    "recursion_not_returned",
                    "WARNING",
                    f"recursive {func_name}() not returned"
                )
                # Also check for unchanged args
                self._check_unchanged_recursive_args(func_node, stmt.value, func_name)
            return

        # Check for unchanged args in returned recursive calls
        if isinstance(stmt, ast.Return) and stmt.value:
            for node in ast.walk(stmt.value):
                if self._is_recursive_call(node, func_name):
                    self._check_unchanged_recursive_args(func_node, node, func_name)

        # Check compound statements
        if isinstance(stmt, ast.If):
            for child_stmt in stmt.body + stmt.orelse:
                self._check_recursion_in_statement(child_stmt, func_name, func_node)
        elif isinstance(stmt, (ast.For, ast.While)):
            for child_stmt in stmt.body + stmt.orelse:
                self._check_recursion_in_statement(child_stmt, func_name, func_node)
        elif isinstance(stmt, ast.Try):
            for child_stmt in stmt.body + stmt.orelse + stmt.finalbody:
                self._check_recursion_in_statement(child_stmt, func_name, func_node)
            for handler in stmt.handlers:
                for child_stmt in handler.body:
                    self._check_recursion_in_statement(child_stmt, func_name, func_node)
        elif isinstance(stmt, ast.With):
            for child_stmt in stmt.body:
                self._check_recursion_in_statement(child_stmt, func_name, func_node)

    def _is_recursive_call(self, node: ast.AST, func_name: str) -> bool:
        """Check if a node is a recursive call to func_name."""
        return (isinstance(node, ast.Call) and
                isinstance(node.func, ast.Name) and
                node.func.id == func_name)

    def _check_unchanged_recursive_args(self, func_node: ast.FunctionDef, call_node: ast.Call, func_name: str):
        """Check if recursive call passes unchanged arguments."""
        # Get parameter names (excluding parameters with defaults that look like indices/counters)
        param_names = [arg.arg for arg in func_node.args.args]
        defaults_start = len(param_names) - len(func_node.args.defaults)

        # Check if any positional arg is passed unchanged
        for i, (param_name, call_arg) in enumerate(zip(param_names, call_node.args)):
            if isinstance(call_arg, ast.Name) and call_arg.id == param_name:
                # This parameter is passed unchanged - could be infinite recursion
                # Only flag if it's the first/primary argument AND it's not a collection type
                # (collections like lists are commonly passed unchanged while indices change)
                if i == 0:
                    # Check if other arguments are changing (suggesting this is an iteration pattern)
                    # If there are more args in the call and at least one is different from params,
                    # this is likely intentional (e.g., fn(lst, idx+1) is fine)
                    other_args_change = False
                    for j, (pname, carg) in enumerate(zip(param_names[1:], call_node.args[1:]), start=1):
                        if not (isinstance(carg, ast.Name) and carg.id == pname):
                            other_args_change = True
                            break

                    # Only flag if no other args are changing
                    if not other_args_change:
                        self._add_issue(
                            call_node,
                            "recursion_unchanged_arg",
                            "ERROR",
                            f"recursive {func_name}({param_name}) unchanged"
                        )

    def visit_ListComp(self, node: ast.ListComp):
        """Check list comprehensions for issues."""
        self._check_comprehension_shadowing(node)
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp):
        """Check set comprehensions for issues."""
        self._check_comprehension_shadowing(node)
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp):
        """Check dict comprehensions for issues."""
        self._check_comprehension_shadowing(node)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp):
        """Check generator expressions for issues."""
        self._check_comprehension_shadowing(node)
        self.generic_visit(node)

    def _check_comprehension_shadowing(self, node):
        """Check for variable shadowing in nested comprehensions."""
        # Collect all loop variable names at each nesting level
        def get_comp_vars(comp_node) -> Set[str]:
            """Get all loop variable names from a comprehension."""
            vars_set = set()
            generators = getattr(comp_node, 'generators', [])
            for gen in generators:
                if isinstance(gen.target, ast.Name):
                    vars_set.add(gen.target.id)
                elif isinstance(gen.target, ast.Tuple):
                    for elt in gen.target.elts:
                        if isinstance(elt, ast.Name):
                            vars_set.add(elt.id)
            return vars_set

        outer_vars = get_comp_vars(node)

        # Check for nested comprehensions in:
        # - The element expression (node.elt for ListComp/SetComp/GeneratorExp, node.key/value for DictComp)
        # - The iter and ifs of each generator
        nodes_to_check = []
        if hasattr(node, 'elt'):
            nodes_to_check.append(node.elt)
        if hasattr(node, 'key'):
            nodes_to_check.append(node.key)
        if hasattr(node, 'value'):
            nodes_to_check.append(node.value)
        for gen in node.generators:
            nodes_to_check.append(gen.iter)
            nodes_to_check.extend(gen.ifs)

        for check_node in nodes_to_check:
            for child in ast.walk(check_node):
                if isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    inner_vars = get_comp_vars(child)
                    shadowed = outer_vars & inner_vars
                    if shadowed:
                        self._add_issue(
                            child,
                            "comprehension_shadowing",
                            "WARNING",
                            f"shadowed: {shadowed}"
                        )

    def visit_Call(self, node: ast.Call):
        """Check function calls for various issues."""
        self._check_namedtuple_positional(node)
        self._check_reduction_in_numpy_elementwise(node)
        self.generic_visit(node)

    def _check_namedtuple_positional(self, node: ast.Call):
        """Flag NamedTuple instantiation with all positional args (heuristic)."""
        # This is a heuristic - we look for calls where the function name
        # looks like a class (PascalCase) and has multiple positional args
        # with no keyword args
        if isinstance(node.func, ast.Name):
            name = node.func.id
            # Check if looks like a class name (PascalCase)
            if name and name[0].isupper() and not name.isupper():
                # Has multiple positional args and no keyword args
                if len(node.args) >= 2 and not node.keywords:
                    self._add_issue(
                        node,
                        "namedtuple_positional",
                        "WARNING",
                        f"NamedTuple {name}() with positional args - use keyword args for clarity"
                    )

    def visit_BinOp(self, node: ast.BinOp):
        """Check binary operations for broadcasting issues."""
        self._check_reduction_in_binop(node.left)
        self._check_reduction_in_binop(node.right)
        self.generic_visit(node)

    def _check_reduction_in_binop(self, node: ast.expr):
        """Flag reduction-with-axis directly in binary op (no keepdims, not subscripted)."""
        # Must be a direct Call, not Subscript (which would be result[:, None])
        # Also not a method call like .reshape() on the result
        if not isinstance(node, ast.Call):
            return

        reduction_funcs = ('sum', 'mean', 'min', 'max', 'std', 'var', 'prod', 'any', 'all')

        # Check for np.{reduction}(...) - function style
        is_np_func = (isinstance(node.func, ast.Attribute) and
                      isinstance(node.func.value, ast.Name) and
                      node.func.value.id == 'np' and
                      node.func.attr in reduction_funcs)

        # Check for arr.{reduction}(...) - method style (any expression.method)
        is_method = (isinstance(node.func, ast.Attribute) and
                     node.func.attr in reduction_funcs and
                     not (isinstance(node.func.value, ast.Name) and node.func.value.id == 'np'))

        if not (is_np_func or is_method):
            return

        func_name = node.func.attr

        # Extract axis value
        axis_value = None
        has_axis = False

        # Check positional arg (axis is 2nd arg for np functions, 1st for methods)
        if is_np_func and len(node.args) >= 2:
            has_axis = True
            axis_value = node.args[1]
        elif is_method and len(node.args) >= 1:
            has_axis = True
            axis_value = node.args[0]

        # Check keyword arg
        has_keepdims = False
        for kw in node.keywords:
            if kw.arg == 'axis':
                has_axis = True
                axis_value = kw.value
            if kw.arg == 'keepdims':
                has_keepdims = True

        if not has_axis or has_keepdims:
            return

        # Skip axis=0 - this is a common correct pattern (feature normalization)
        # axis=0 reductions broadcast correctly because numpy aligns from the right
        if isinstance(axis_value, ast.Constant) and axis_value.value == 0:
            return

        # Determine the style for the message
        style = "np." if is_np_func else "."
        self._add_issue(
            node,
            "reduction_no_keepdims",
            "WARNING",
            f"{style}{func_name}(axis=) in binop without keepdims"
        )

    def _check_reduction_in_numpy_elementwise(self, node: ast.Call):
        """Check np.multiply/divide/add/subtract/where for reduction arguments."""
        if not (isinstance(node.func, ast.Attribute) and
                isinstance(node.func.value, ast.Name) and
                node.func.value.id == 'np'):
            return

        # Check np.{multiply,divide,add,subtract,power}
        elementwise_funcs = ('multiply', 'divide', 'add', 'subtract', 'power')
        if node.func.attr in elementwise_funcs:
            for arg in node.args:
                self._check_reduction_in_binop(arg)

        # Check np.where with 3 args (condition, x, y)
        # The condition often compares against a reduction
        if node.func.attr == 'where' and len(node.args) >= 3:
            # Check if any argument contains a reduction directly
            for arg in node.args:
                self._check_reduction_in_binop(arg)
                # Also check inside comparisons in the condition
                if isinstance(arg, ast.Compare):
                    self._check_reduction_in_binop(arg.left)
                    for comparator in arg.comparators:
                        self._check_reduction_in_binop(comparator)


def check_ast_patterns(content: str, filename: str) -> List[LintIssue]:
    """Run all AST-based pattern checks on file content."""
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        return [LintIssue(
            file=filename,
            line=e.lineno or 0,
            column=e.offset or 0,
            rule_id="syntax_error",
            severity="ERROR",
            message=f"Syntax error: {e.msg}"
        )]

    source_lines = content.split('\n')
    checker = ASTChecker(filename, source_lines)
    checker.visit(tree)
    return checker.issues


# =============================================================================
# Main Scanning Functions
# =============================================================================

def scan_file(filepath: Path) -> List[LintIssue]:
    """Scan a single file for issues."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        return [LintIssue(
            file=str(filepath),
            line=0,
            column=0,
            rule_id="read_error",
            severity="ERROR",
            message=f"Could not read file: {e}"
        )]

    issues = []
    issues.extend(check_regex_patterns(content, str(filepath)))
    issues.extend(check_ast_patterns(content, str(filepath)))

    # Sort by line number
    issues.sort(key=lambda x: (x.line, x.column))

    # Deduplicate (regex and AST may flag same issue)
    seen = set()
    unique_issues = []
    for issue in issues:
        key = (issue.file, issue.line, issue.rule_id)
        if key not in seen:
            seen.add(key)
            unique_issues.append(issue)

    return unique_issues


# Directories to exclude by default when scanning
DEFAULT_EXCLUDES = {
    'tests', 'test', 'custom_tests', 'custom',
    '.git', '__pycache__', '.venv', 'venv', 'env',
    'node_modules', '.tox', '.pytest_cache', '.mypy_cache',
    'build', 'dist', 'egg-info', '.eggs',
}


def should_exclude(filepath: Path, excludes: Set[str]) -> bool:
    """Check if filepath should be excluded based on directory names or filename patterns."""
    parts = filepath.parts
    for part in parts:
        if part in excludes or part.endswith('.egg-info'):
            return True
    # Also exclude test files (test_*.py, *_test.py)
    name = filepath.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return True
    return False


def scan_directory(dirpath: Path, recursive: bool = True, excludes: Optional[Set[str]] = None) -> Dict[str, List[LintIssue]]:
    """Scan all Python files in a directory."""
    if excludes is None:
        excludes = DEFAULT_EXCLUDES

    results = {}

    pattern = "**/*.py" if recursive else "*.py"
    for filepath in dirpath.glob(pattern):
        if filepath.is_file() and not should_exclude(filepath, excludes):
            issues = scan_file(filepath)
            if issues:
                results[str(filepath)] = issues

    return results


def highlight_code(code: str) -> str:
    """Syntax highlight Python code if pygments is available."""
    if PYGMENTS_AVAILABLE:
        return highlight(code, PythonLexer(), Terminal256Formatter(style='monokai')).rstrip()
    return code


def format_issue(issue: LintIssue, show_snippet: bool = True) -> str:
    """Format a single issue for display."""
    severity_colors = {
        "ERROR": "\033[91m",    # Red
        "WARNING": "\033[93m",  # Yellow
        "INFO": "\033[94m",     # Blue
    }
    reset = "\033[0m"

    color = severity_colors.get(issue.severity, "")
    sev_short = {"ERROR": "E", "WARNING": "W", "INFO": "I"}.get(issue.severity, "?")

    loc = f"{issue.file}:{issue.line}"
    line = f"{color}{sev_short}{reset} {loc}: {issue.message}"

    if show_snippet and issue.code_snippet:
        highlighted = highlight_code(issue.code_snippet)
        line += f"\n    {highlighted}"

    return line


def print_report(results: Dict[str, List[LintIssue]], show_snippets: bool = True):
    """Print a formatted report of all issues."""
    total_errors = 0
    total_warnings = 0
    total_info = 0

    for filepath, issues in sorted(results.items()):
        for issue in issues:
            print(format_issue(issue, show_snippets))

            if issue.severity == "ERROR":
                total_errors += 1
            elif issue.severity == "WARNING":
                total_warnings += 1
            else:
                total_info += 1

    def plural(n, word):
        return f"{n} {word}" if n == 1 else f"{n} {word}s"

    parts = []
    if total_errors:
        parts.append(f"\033[91m{plural(total_errors, 'error')}\033[0m")
    if total_warnings:
        parts.append(f"\033[93m{plural(total_warnings, 'warning')}\033[0m")
    if total_info:
        parts.append(f"\033[94m{plural(total_info, 'info')}\033[0m")

    if parts:
        print(f"\n{', '.join(parts)}")
    else:
        print("\nno issues")

    return total_errors, total_warnings, total_info


# =============================================================================
# CLI Entry Point
# =============================================================================

def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <file_or_directory>")
        print(f"       {sys.argv[0]} .  # Scan current directory")
        sys.exit(1)

    target = Path(sys.argv[1])

    if not target.exists():
        print(f"Error: '{target}' does not exist")
        sys.exit(1)

    if target.is_file():
        issues = scan_file(target)
        results = {str(target): issues} if issues else {}
    else:
        results = scan_directory(target)

    if not results:
        print("No issues found.")
        sys.exit(0)

    errors, warnings, info = print_report(results)

    # Exit with error code if there are errors
    sys.exit(1 if errors > 0 else 0)


if __name__ == "__main__":
    main()
