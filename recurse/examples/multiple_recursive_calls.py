"""
Multiple Recursive Calls Errors

These functions make multiple recursive calls (common in trees and
divide-and-conquer) but have bugs in how the calls are made or
which branches are processed.
"""


def tree_contains(node, target):
    """Check if BST contains target but checks wrong branches.

    Bug: Always searches both children instead of using BST property.
    This isn't wrong per se, but then the BST optimization is broken.
    More critically: returns True for left but doesn't check right.
    """
    if node is None:
        return False

    if node['value'] == target:
        return True

    # Wrong: only returns left result, ignores right
    return tree_contains(node.get('left'), target)


# Corrected version:
# def tree_contains(node, target):
#     if node is None:
#         return False
#     if node['value'] == target:
#         return True
#     if target < node['value']:
#         return tree_contains(node.get('left'), target)
#     return tree_contains(node.get('right'), target)


def max_path_sum(node):
    """Find max root-to-leaf path sum but adds both paths.

    Bug: Adds left AND right instead of taking max.
    Result: Returns sum of all nodes, not max path
    """
    if node is None:
        return 0

    if node.get('left') is None and node.get('right') is None:
        return node['value']

    left_sum = max_path_sum(node.get('left'))
    right_sum = max_path_sum(node.get('right'))

    # Wrong: should be max(left_sum, right_sum)
    return node['value'] + left_sum + right_sum


# Corrected version:
# def max_path_sum(node):
#     if node is None:
#         return 0
#     if node.get('left') is None and node.get('right') is None:
#         return node['value']
#     left_sum = max_path_sum(node.get('left'))
#     right_sum = max_path_sum(node.get('right'))
#     return node['value'] + max(left_sum, right_sum)


def quicksort(arr):
    """Quicksort but partition logic is wrong.

    Bug: Includes pivot in both recursive calls.
    Result: Infinite recursion when there are duplicates
    """
    if len(arr) <= 1:
        return arr

    pivot = arr[0]

    # Wrong: includes pivot in both partitions
    left = [x for x in arr if x <= pivot]  # pivot included here
    right = [x for x in arr if x >= pivot]  # and here!

    return quicksort(left) + quicksort(right)


# Corrected version:
# def quicksort(arr):
#     if len(arr) <= 1:
#         return arr
#     pivot = arr[0]
#     left = [x for x in arr[1:] if x < pivot]
#     middle = [x for x in arr if x == pivot]
#     right = [x for x in arr[1:] if x > pivot]
#     return quicksort(left) + middle + quicksort(right)


def tree_depth(node):
    """Find tree depth but only checks one child.

    Bug: Only recurses on left child, ignores right.
    Result: Returns depth of leftmost path only
    """
    if node is None:
        return 0

    left_depth = tree_depth(node.get('left'))
    # Wrong: forgot to check right

    return 1 + left_depth


# Corrected version:
# def tree_depth(node):
#     if node is None:
#         return 0
#     left_depth = tree_depth(node.get('left'))
#     right_depth = tree_depth(node.get('right'))
#     return 1 + max(left_depth, right_depth)


def fibonacci_memo(n, memo={}):
    """Fibonacci with memoization but wrong recursive formula.

    Bug: Uses n-1 twice instead of n-1 and n-2.
    Result: Returns wrong Fibonacci numbers
    """
    if n in memo:
        return memo[n]

    if n <= 1:
        return n

    # Wrong: should be fibonacci_memo(n-1) + fibonacci_memo(n-2)
    result = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 1, memo)
    memo[n] = result
    return result


# Corrected version:
# def fibonacci_memo(n, memo=None):
#     if memo is None:
#         memo = {}
#     if n in memo:
#         return memo[n]
#     if n <= 1:
#         return n
#     result = fibonacci_memo(n - 1, memo) + fibonacci_memo(n - 2, memo)
#     memo[n] = result
#     return result


def count_paths(grid, row=0, col=0):
    """Count paths in grid but wrong boundary checks.

    Bug: Uses 'and' instead of 'or' for boundary check.
    Result: Doesn't stop at boundaries correctly
    """
    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    # Wrong: should be 'or' - stop if EITHER boundary is exceeded
    if row >= rows and col >= cols:
        return 0

    if row == rows - 1 and col == cols - 1:
        return 1

    # This will cause index errors
    right = count_paths(grid, row, col + 1)
    down = count_paths(grid, row + 1, col)

    return right + down


# Corrected version:
# def count_paths(grid, row=0, col=0):
#     rows = len(grid)
#     cols = len(grid[0]) if grid else 0
#     if row >= rows or col >= cols:  # 'or' not 'and'
#         return 0
#     if row == rows - 1 and col == cols - 1:
#         return 1
#     right = count_paths(grid, row, col + 1)
#     down = count_paths(grid, row + 1, col)
#     return right + down


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(100)

    # Build a BST
    #       5
    #      / \
    #     3   7
    #    / \
    #   1   4
    bst = {
        'value': 5,
        'left': {
            'value': 3,
            'left': {'value': 1, 'left': None, 'right': None},
            'right': {'value': 4, 'left': None, 'right': None}
        },
        'right': {'value': 7, 'left': None, 'right': None}
    }

    print("Testing tree_contains(bst, 7)...")
    print("Expected: True")
    print(f"Got: {tree_contains(bst, 7)}")

    print("\nTesting tree_contains(bst, 4)...")
    print("Expected: True")
    print(f"Got: {tree_contains(bst, 4)}")

    print("\nTesting max_path_sum...")
    #       1
    #      / \
    #     2   3
    tree = {
        'value': 1,
        'left': {'value': 2, 'left': None, 'right': None},
        'right': {'value': 3, 'left': None, 'right': None}
    }
    print("Tree: 1 -> 2, 3")
    print("Expected max path sum: 4 (1 -> 3)")
    print(f"Got: {max_path_sum(tree)}")

    print("\nTesting quicksort([3, 1, 4, 1, 5, 9, 2, 6])...")
    print("Expected: [1, 1, 2, 3, 4, 5, 6, 9]")
    try:
        result = quicksort([3, 1, 4, 1, 5, 9, 2, 6])
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting tree_depth on unbalanced tree...")
    #   1
    #  / \
    # 2   3
    #      \
    #       4
    #        \
    #         5
    unbalanced = {
        'value': 1,
        'left': {'value': 2, 'left': None, 'right': None},
        'right': {
            'value': 3,
            'left': None,
            'right': {
                'value': 4,
                'left': None,
                'right': {'value': 5, 'left': None, 'right': None}
            }
        }
    }
    print("Expected depth: 4")
    print(f"Got: {tree_depth(unbalanced)}")

    print("\nTesting fibonacci_memo for n=0 to 8...")
    print("Expected: 0, 1, 1, 2, 3, 5, 8, 13, 21")
    # Clear memo between tests
    print("Got:     ", ", ".join(str(fibonacci_memo(i, {})) for i in range(9)))

    print("\nTesting count_paths on 3x3 grid...")
    grid = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    print("Expected: 6")
    try:
        result = count_paths(grid)
        print(f"Got: {result}")
    except (IndexError, RecursionError) as e:
        print(f"Error: {type(e).__name__}: {e}")
