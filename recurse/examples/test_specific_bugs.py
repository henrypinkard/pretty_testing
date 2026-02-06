"""
BUGGY versions of test-specific patterns.
Run with trace to see how bugs manifest.
"""

import sys
sys.path.insert(0, '..')

from collections import namedtuple
import numpy as np
# _rtrace is auto-injected into builtins via site-packages (no import needed)

sys.setrecursionlimit(30)

Node = namedtuple('Node', ['value', 'left', 'right'])

def make_tree():
    return Node(
        value=10,
        left=Node(value=5, left=Node(3, None, None), right=Node(7, None, None)),
        right=Node(value=15, left=None, right=Node(20, None, None))
    )

tree = make_tree()

# ============================================================
# BUG 1: NamedTuple - Wrong field access
# ============================================================
print("=" * 60)
print("BUG 1: Wrong field access (node[0] vs node.value)")
print("=" * 60)

@_rtrace
def tree_sum_wrong_access(node):
    """Bug: Using index instead of attribute."""
    if node is None:
        return 0
    # BUG: node[0] works but is confusing and error-prone
    # Should be node.value
    return node[0] + tree_sum_wrong_access(node[1]) + tree_sum_wrong_access(node[2])

result = tree_sum_wrong_access(tree)
print(f"Result: {result} (works but fragile - index vs attribute)")

# ============================================================
# BUG 2: NamedTuple - Only checking one child
# ============================================================
print("\n" + "=" * 60)
print("BUG 2: BST search only checks left child")
print("=" * 60)

@_rtrace
def tree_find_left_only(node, target):
    """Bug: Only recurses left, never right."""
    if node is None:
        return False
    if node.value == target:
        return True
    # BUG: Should check right when target > node.value
    return tree_find_left_only(node.left, target)

result = tree_find_left_only(tree, 20)  # 20 is in right subtree
print(f"Find 20: {result} (expected: True, but only checks left)")

# ============================================================
# BUG 3: Inorder - Wrong order of operations
# ============================================================
print("\n" + "=" * 60)
print("BUG 3: Inorder with wrong visit order (preorder instead)")
print("=" * 60)

@_rtrace
def inorder_wrong_order(node):
    """Bug: Visits node before left (preorder instead of inorder)."""
    if node is None:
        return []
    # BUG: Should be left + [value] + right
    return [node.value] + inorder_wrong_order(node.left) + inorder_wrong_order(node.right)

result = inorder_wrong_order(tree)
print(f"Got:      {result}")
print(f"Expected: [3, 5, 7, 10, 15, 20] (inorder)")

# ============================================================
# BUG 4: Class method - Forgetting to update accumulator
# ============================================================
print("\n" + "=" * 60)
print("BUG 4: Class method - accumulator not passed correctly")
print("=" * 60)

class TokenProcessorBuggy:
    def __init__(self, tokens):
        self.tokens = tokens

    @_rtrace
    def process(self, idx=0, acc=0):
        """Bug: Doesn't pass updated accumulator."""
        if idx >= len(self.tokens):
            return acc
        score = self.tokens[idx] * (idx + 1)
        # BUG: Should pass acc + score, not just score
        return self.process(idx + 1, score)

processor = TokenProcessorBuggy([1, 2, 3, 4, 5])
result = processor.process()
print(f"Result: {result} (expected: 55, got last score only)")

# ============================================================
# BUG 5: Array recursion - Off by one in slice
# ============================================================
print("\n" + "=" * 60)
print("BUG 5: Array recursion - off by one slice")
print("=" * 60)

@_rtrace(max_depth=10)
def recursive_sum_offbyone(arr):
    """Bug: Wrong slice causes missing elements."""
    if len(arr) == 0:
        return 0
    if len(arr) == 1:
        return arr[0]
    mid = len(arr) // 2
    # BUG: Should be arr[:mid] and arr[mid:], not arr[:mid-1]
    return recursive_sum_offbyone(arr[:mid-1]) + recursive_sum_offbyone(arr[mid:])

arr = np.array([1, 2, 3, 4, 5, 6, 7, 8])
result = recursive_sum_offbyone(arr)
print(f"Result: {result} (expected: 36, missing elements due to slice bug)")

# ============================================================
# BUG 6: Wrong base case value
# ============================================================
print("\n" + "=" * 60)
print("BUG 6: Wrong base case for max (returns 0 for empty)")
print("=" * 60)

@_rtrace
def recursive_max_wrong_base(arr):
    """Bug: Returns 0 for empty instead of -inf."""
    if len(arr) == 0:
        return 0  # BUG: Should be float('-inf')
    if len(arr) == 1:
        return arr[0]
    mid = len(arr) // 2
    return max(recursive_max_wrong_base(arr[:mid]), recursive_max_wrong_base(arr[mid:]))

# This works for positive numbers but fails for all negative
arr = np.array([-5, -3, -8, -1])
result = recursive_max_wrong_base(arr)
print(f"Result: {result} (expected: -1, got wrong due to 0 base case)")

# ============================================================
# BUG 7: Mutable default argument
# ============================================================
print("\n" + "=" * 60)
print("BUG 7: Mutable default argument (list)")
print("=" * 60)

@_rtrace
def collect_values_mutable_default(node, result=[]):
    """Bug: Mutable default accumulates across calls."""
    if node is None:
        return result
    result.append(node.value)
    collect_values_mutable_default(node.left, result)
    collect_values_mutable_default(node.right, result)
    return result

small_tree = Node(1, Node(2, None, None), None)

print("First call:")
result1 = collect_values_mutable_default(small_tree)
print(f"Result 1: {result1}")

print("\nSecond call (should be independent):")
result2 = collect_values_mutable_default(small_tree)
print(f"Result 2: {result2} (BUG: accumulated from first call!)")

# ============================================================
# BUG 8: Not reducing - same arguments
# ============================================================
print("\n" + "=" * 60)
print("BUG 8: Index not incrementing")
print("=" * 60)

@_rtrace(max_depth=8)
def sum_array_stuck(arr, idx=0, total=0):
    """Bug: idx not incremented."""
    if idx >= len(arr):
        return total
    # BUG: Should be idx + 1
    return sum_array_stuck(arr, idx, total + arr[idx])

try:
    result = sum_array_stuck(np.array([1, 2, 3]))
except RecursionError:
    print("RecursionError: idx stays at 0")

# ============================================================
# BUG 9: Wrong return in class method
# ============================================================
print("\n" + "=" * 60)
print("BUG 9: Missing return in recursive class method")
print("=" * 60)

class TreeAnalyzer:
    def __init__(self, tree):
        self.tree = tree

    @_rtrace
    def count_nodes(self, node=None, first_call=True):
        """Bug: Missing return statement."""
        if first_call:
            node = self.tree
        if node is None:
            return 0
        left = self.count_nodes(node.left, False)
        right = self.count_nodes(node.right, False)
        # BUG: Missing return!
        1 + left + right

try:
    analyzer = TreeAnalyzer(tree)
    result = analyzer.count_nodes()
    print(f"Result: {result} (expected: 6)")
except TypeError as e:
    print(f"TypeError: {e}")

# ============================================================
# BUG 10: NumPy array comparison issue
# ============================================================
print("\n" + "=" * 60)
print("BUG 10: Using Python len() check wrong with NumPy")
print("=" * 60)

@_rtrace
def find_target_numpy_bug(arr, target, idx=0):
    """Bug: Comparing numpy scalar incorrectly."""
    if idx >= len(arr):
        return -1
    # This works, but common bug is: if arr[idx] is target (identity vs equality)
    if arr[idx] is target:  # BUG: should use ==
        return idx
    return find_target_numpy_bug(arr, target, idx + 1)

arr = np.array([1, 2, 3, 4, 5])
result = find_target_numpy_bug(arr, 3)
print(f"Find 3: {result} (expected: 2, got -1 due to 'is' vs '==')")
