"""
Recursion examples matching the test patterns:
- Classes/methods
- NamedTuple tree structures
- NumPy array operations
- Transformer-inspired patterns
"""

import sys
sys.path.insert(0, '..')

from collections import namedtuple
import numpy as np
# _rtrace is auto-injected into builtins via site-packages (no import needed)

# Set recursion limit AFTER imports (numpy needs higher limit to load)
sys.setrecursionlimit(50)

# ============================================================
# PATTERN 1: NamedTuple Tree Structures
# ============================================================

Node = namedtuple('Node', ['value', 'left', 'right'])

def make_tree():
    """Create a sample binary tree using NamedTuple."""
    return Node(
        value=10,
        left=Node(value=5, left=Node(3, None, None), right=Node(7, None, None)),
        right=Node(value=15, left=None, right=Node(20, None, None))
    )

print("=" * 60)
print("PATTERN 1: NamedTuple Tree - Sum all values")
print("=" * 60)

@traceit_
def tree_sum(node):
    """Sum all values in a NamedTuple tree."""
    if node is None:
        return 0
    return node.value + tree_sum(node.left) + tree_sum(node.right)

tree = make_tree()
result = tree_sum(tree)
print(f"Result: {result} (expected: 60)")

# ============================================================
# PATTERN 2: NamedTuple Tree - Find/Search
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 2: NamedTuple Tree - Find value")
print("=" * 60)

@traceit_
def tree_find(node, target):
    """Find a value in a BST using NamedTuple."""
    if node is None:
        return False
    if node.value == target:
        return True
    if target < node.value:
        return tree_find(node.left, target)
    return tree_find(node.right, target)

result = tree_find(tree, 7)
print(f"Find 7: {result} (expected: True)")

result = tree_find(tree, 99)
print(f"Find 99: {result} (expected: False)")

# ============================================================
# PATTERN 3: NamedTuple Tree - Collect to list
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 3: NamedTuple Tree - Inorder traversal to list")
print("=" * 60)

@traceit_
def inorder(node):
    """Return inorder traversal as a list."""
    if node is None:
        return []
    return inorder(node.left) + [node.value] + inorder(node.right)

result = inorder(tree)
print(f"Inorder: {result}")

# ============================================================
# PATTERN 4: Class with recursive method
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 4: Class with recursive method")
print("=" * 60)

class TokenProcessor:
    """Process tokens recursively (transformer-inspired)."""

    def __init__(self, tokens):
        self.tokens = tokens

    @traceit_
    def process(self, idx=0, acc=0):
        """Recursively process tokens, accumulating a score."""
        if idx >= len(self.tokens):
            return acc
        # Simple scoring: add token value
        score = self.tokens[idx] * (idx + 1)
        return self.process(idx + 1, acc + score)

processor = TokenProcessor([1, 2, 3, 4, 5])
result = processor.process()
print(f"Result: {result} (expected: 1*1 + 2*2 + 3*3 + 4*4 + 5*5 = 55)")

# ============================================================
# PATTERN 5: Recursive array splitting (divide & conquer)
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 5: Recursive array max (divide & conquer)")
print("=" * 60)

@traceit_(max_len=30)
def recursive_max(arr):
    """Find max by recursively splitting array."""
    if len(arr) == 0:
        return float('-inf')
    if len(arr) == 1:
        return arr[0]
    mid = len(arr) // 2
    left_max = recursive_max(arr[:mid])
    right_max = recursive_max(arr[mid:])
    return max(left_max, right_max)

arr = np.array([3, 1, 4, 1, 5, 9, 2, 6])
result = recursive_max(arr)
print(f"Max: {result} (expected: 9)")

# ============================================================
# PATTERN 6: Recursive histogram binning
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 6: Recursive count in ranges")
print("=" * 60)

@traceit_
def count_in_range(arr, lo, hi):
    """Count elements in [lo, hi] range recursively."""
    if len(arr) == 0:
        return 0
    if len(arr) == 1:
        return 1 if lo <= arr[0] <= hi else 0
    mid = len(arr) // 2
    return count_in_range(arr[:mid], lo, hi) + count_in_range(arr[mid:], lo, hi)

arr = np.array([1, 5, 3, 8, 2, 9, 4, 7])
result = count_in_range(arr, 3, 7)
print(f"Count in [3,7]: {result} (expected: 4)")

# ============================================================
# PATTERN 7: Attention-like recursive aggregation
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 7: Recursive weighted sum (attention-like)")
print("=" * 60)

@traceit_(max_len=35)
def weighted_aggregate(values, weights, idx=0):
    """Recursively compute weighted sum."""
    if idx >= len(values):
        return 0.0
    return values[idx] * weights[idx] + weighted_aggregate(values, weights, idx + 1)

values = np.array([1.0, 2.0, 3.0, 4.0])
weights = np.array([0.1, 0.2, 0.3, 0.4])  # Sums to 1.0
result = weighted_aggregate(values, weights)
print(f"Weighted sum: {result:.2f} (expected: 3.00)")

# ============================================================
# PATTERN 8: Recursive softmax normalization
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 8: Recursive array normalization")
print("=" * 60)

@traceit_(max_len=40)
def recursive_normalize(arr, total=None, idx=0, result=None):
    """Normalize array values to sum to 1 (softmax-like)."""
    if result is None:
        result = np.zeros_like(arr, dtype=float)
    if total is None:
        total = np.sum(arr)

    if idx >= len(arr):
        return result

    result[idx] = arr[idx] / total
    return recursive_normalize(arr, total, idx + 1, result)

arr = np.array([1, 2, 3, 4])
result = recursive_normalize(arr)
print(f"Normalized: {result} (should sum to 1.0, sum={result.sum():.2f})")

# ============================================================
# PATTERN 9: Recursive sequence generation
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 9: Recursive sequence generation")
print("=" * 60)

@traceit_
def generate_sequence(n, seq=None):
    """Generate sequence where each element is sum of previous two."""
    if seq is None:
        seq = [0, 1]
    if len(seq) >= n:
        return seq[:n]
    next_val = seq[-1] + seq[-2]
    return generate_sequence(n, seq + [next_val])

result = generate_sequence(8)
print(f"Sequence: {result}")

# ============================================================
# PATTERN 10: NamedTuple with class - Tree Node operations
# ============================================================

print("\n" + "=" * 60)
print("PATTERN 10: Tree depth calculation")
print("=" * 60)

@traceit_
def tree_depth(node):
    """Calculate depth of NamedTuple tree."""
    if node is None:
        return 0
    return 1 + max(tree_depth(node.left), tree_depth(node.right))

result = tree_depth(tree)
print(f"Depth: {result} (expected: 3)")
