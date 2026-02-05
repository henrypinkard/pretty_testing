"""Test trace decorator against buggy recursive functions."""

import sys
sys.setrecursionlimit(25)

from trace import trace

# ============================================================
# TEST 1: Missing base case - should show infinite descent
# ============================================================
print("=" * 60)
print("BUG: Missing base case (factorial)")
print("=" * 60)

@trace(max_depth=10)
def factorial_no_base(n):
    return n * factorial_no_base(n - 1)

try:
    factorial_no_base(5)
except RecursionError:
    print(">>> RecursionError caught - see trace above showing endless descent")

# ============================================================
# TEST 2: Wrong base case - returns wrong value
# ============================================================
print("\n" + "=" * 60)
print("BUG: Wrong base case (factorial returns 0)")
print("=" * 60)

@trace
def factorial_wrong_base(n):
    if n <= 1:
        return 0  # BUG: should be 1
    return n * factorial_wrong_base(n - 1)

result = factorial_wrong_base(5)
print(f">>> Result is {result}, should be 120 - base case returned 0")

# ============================================================
# TEST 3: Not reducing toward base case
# ============================================================
print("\n" + "=" * 60)
print("BUG: Not reducing (same index passed)")
print("=" * 60)

@trace(max_depth=8)
def find_element_stuck(lst, target, index=0):
    if index >= len(lst):
        return -1
    if lst[index] == target:
        return index
    return find_element_stuck(lst, target, index)  # BUG: should be index + 1

try:
    find_element_stuck([1, 2, 3], 3)
except RecursionError:
    print(">>> RecursionError - index stays at 0 every call")

# ============================================================
# TEST 4: Forgetting return
# ============================================================
print("\n" + "=" * 60)
print("BUG: Forgetting return (returns None)")
print("=" * 60)

@trace
def sum_to_n_no_return(n):
    if n <= 0:
        return 0
    sum_to_n_no_return(n - 1) + n  # BUG: missing return

try:
    result = sum_to_n_no_return(5)
    print(f">>> Result: {result}")
except TypeError as e:
    print(f">>> TypeError: {e}")

# ============================================================
# TEST 5: Wrong argument reduction
# ============================================================
print("\n" + "=" * 60)
print("BUG: Wrong slice (reverses in wrong direction)")
print("=" * 60)

@trace
def reverse_wrong(lst):
    if len(lst) <= 1:
        return lst
    return [lst[0]] + reverse_wrong(lst[1:])  # BUG: should be [lst[-1]] + reverse(lst[:-1])

result = reverse_wrong([1, 2, 3, 4])
print(f">>> Result: {result}, should be [4, 3, 2, 1]")

# ============================================================
# TEST 6: Wrong combination/merge
# ============================================================
print("\n" + "=" * 60)
print("BUG: Wrong combination (adding instead of max)")
print("=" * 60)

@trace
def max_path_sum_wrong(node):
    if node is None:
        return 0
    if node.get('left') is None and node.get('right') is None:
        return node['value']
    left = max_path_sum_wrong(node.get('left'))
    right = max_path_sum_wrong(node.get('right'))
    return node['value'] + left + right  # BUG: should use max(left, right)

tree = {
    'value': 1,
    'left': {'value': 2, 'left': None, 'right': None},
    'right': {'value': 3, 'left': None, 'right': None}
}
result = max_path_sum_wrong(tree)
print(f">>> Result: {result}, should be 4 (1+3), not 6 (1+2+3)")

# ============================================================
# TEST 7: Accumulator mistake
# ============================================================
print("\n" + "=" * 60)
print("BUG: Accumulator reset on each call")
print("=" * 60)

@trace
def sum_list_reset_acc(lst, acc=0):
    if not lst:
        return acc
    acc = 0  # BUG: resets accumulator
    acc += lst[0]
    return sum_list_reset_acc(lst[1:], acc)

result = sum_list_reset_acc([1, 2, 3, 4, 5])
print(f">>> Result: {result}, should be 15")

# ============================================================
# TEST 8: Multiple recursive calls - wrong branch
# ============================================================
print("\n" + "=" * 60)
print("BUG: Only checks left branch in BST")
print("=" * 60)

@trace
def tree_contains_wrong(node, target):
    if node is None:
        return False
    if node['value'] == target:
        return True
    return tree_contains_wrong(node.get('left'), target)  # BUG: never checks right

bst = {
    'value': 5,
    'left': {'value': 3, 'left': None, 'right': None},
    'right': {'value': 7, 'left': None, 'right': None}
}
result = tree_contains_wrong(bst, 7)
print(f">>> Looking for 7: {result}, should be True")
