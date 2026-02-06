"""Test trace decorator against various recursive patterns."""

import sys
sys.setrecursionlimit(30)

# _rtrace is auto-injected into builtins via site-packages (no import needed)

# Test 1: Simple list recursion
print("=" * 60)
print("TEST 1: List sum (clean output)")
print("=" * 60)

@traceit_
def sum_list(lst):
    if not lst:
        return 0
    return lst[0] + sum_list(lst[1:])

try:
    sum_list([1, 2, 3, 4, 5])
except RecursionError as e:
    print(f"RecursionError: {e}")

# Test 2: Tree structure (complex objects)
print("\n" + "=" * 60)
print("TEST 2: Tree traversal (complex nested dict)")
print("=" * 60)

tree = {
    'value': 1,
    'left': {
        'value': 2,
        'left': {'value': 4, 'left': None, 'right': None},
        'right': {'value': 5, 'left': None, 'right': None}
    },
    'right': {
        'value': 3,
        'left': None,
        'right': None
    }
}

@traceit_
def tree_sum(node):
    if node is None:
        return 0
    return node['value'] + tree_sum(node.get('left')) + tree_sum(node.get('right'))

tree_sum(tree)

# Test 3: Path finding with mutable state
print("\n" + "=" * 60)
print("TEST 3: Path finding (list argument)")
print("=" * 60)

graph = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}

@traceit_
def find_path(graph, start, end, path=None):
    if path is None:
        path = []
    path = path + [start]
    if start == end:
        return path
    if start not in graph:
        return None
    for node in graph[start]:
        if node not in path:
            result = find_path(graph, node, end, path)
            if result:
                return result
    return None

find_path(graph, 'A', 'D')

# Test 4: Binary search (multiple args)
print("\n" + "=" * 60)
print("TEST 4: Binary search (multiple numeric args)")
print("=" * 60)

@traceit_
def binary_search(arr, target, low, high):
    if low > high:
        return -1
    mid = (low + high) // 2
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search(arr, target, mid + 1, high)
    else:
        return binary_search(arr, target, low, mid - 1)

binary_search([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 7, 0, 9)

# Test 5: Fibonacci (to show repeated calls)
print("\n" + "=" * 60)
print("TEST 5: Fibonacci (exponential calls)")
print("=" * 60)

@traceit_
def fib(n):
    if n <= 1:
        return n
    return fib(n-1) + fib(n-2)

fib(5)
