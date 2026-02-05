"""
Forgetting Return Statement Errors

These functions make recursive calls but forget to return the result.
The recursion happens correctly, but the result is lost and None
is returned instead.
"""


def factorial(n):
    """Calculate n! but forgot return on recursive call.

    Bug: Missing 'return' before recursive call.
    Result: Returns None for any n > 1
    """
    if n <= 1:
        return 1
    factorial(n - 1) * n  # Missing return!


# Corrected version:
# def factorial(n):
#     if n <= 1:
#         return 1
#     return factorial(n - 1) * n


def sum_to_n(n):
    """Sum 1 to n but forgot return on recursive call.

    Bug: Missing 'return' before recursive call.
    Result: Returns None for any n > 0
    """
    if n <= 0:
        return 0
    sum_to_n(n - 1) + n  # Missing return!


# Corrected version:
# def sum_to_n(n):
#     if n <= 0:
#         return 0
#     return sum_to_n(n - 1) + n


def find_max(lst):
    """Find maximum in list but forgot return on recursive call.

    Bug: Missing 'return' before recursive call.
    Result: Returns None when list has more than one element
    """
    if len(lst) == 1:
        return lst[0]

    rest_max = find_max(lst[1:])
    if lst[0] > rest_max:
        return lst[0]
    rest_max  # Missing return!


# Corrected version:
# def find_max(lst):
#     if len(lst) == 1:
#         return lst[0]
#     rest_max = find_max(lst[1:])
#     if lst[0] > rest_max:
#         return lst[0]
#     return rest_max


def binary_search(arr, target, low, high):
    """Binary search but forgot return on recursive calls.

    Bug: Missing 'return' on both recursive branches.
    Result: Only returns result if found at first mid, else None
    """
    if low > high:
        return -1

    mid = (low + high) // 2

    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        binary_search(arr, target, mid + 1, high)  # Missing return!
    else:
        binary_search(arr, target, low, mid - 1)   # Missing return!


# Corrected version:
# def binary_search(arr, target, low, high):
#     if low > high:
#         return -1
#     mid = (low + high) // 2
#     if arr[mid] == target:
#         return mid
#     elif arr[mid] < target:
#         return binary_search(arr, target, mid + 1, high)
#     else:
#         return binary_search(arr, target, low, mid - 1)


def tree_height(node):
    """Calculate tree height but forgot return.

    Bug: Missing 'return' when computing max of subtrees.
    Result: Returns None for any tree with children
    """
    if node is None:
        return 0

    left_height = tree_height(node.get('left'))
    right_height = tree_height(node.get('right'))

    1 + max(left_height, right_height)  # Missing return!


# Corrected version:
# def tree_height(node):
#     if node is None:
#         return 0
#     left_height = tree_height(node.get('left'))
#     right_height = tree_height(node.get('right'))
#     return 1 + max(left_height, right_height)


if __name__ == "__main__":
    print("Testing factorial(5)...")
    print("Expected: 120")
    try:
        print(f"Got: {factorial(5)}")
    except TypeError as e:
        print(f"TypeError: {e}")

    print("\nTesting sum_to_n(5)...")
    print("Expected: 15")
    try:
        print(f"Got: {sum_to_n(5)}")
    except TypeError as e:
        print(f"TypeError: {e}")

    print("\nTesting find_max([3, 1, 4, 1, 5, 9, 2, 6])...")
    print("Expected: 9")
    try:
        print(f"Got: {find_max([3, 1, 4, 1, 5, 9, 2, 6])}")
    except TypeError as e:
        print(f"TypeError: {e}")

    print("\nTesting binary_search([1,2,3,4,5,6,7], 5, 0, 6)...")
    print("Expected: 4")
    try:
        print(f"Got: {binary_search([1, 2, 3, 4, 5, 6, 7], 5, 0, 6)}")
    except TypeError as e:
        print(f"TypeError: {e}")

    print("\nTesting tree_height on a tree of height 3...")
    tree = {
        'value': 1,
        'left': {
            'value': 2,
            'left': {'value': 4, 'left': None, 'right': None},
            'right': None
        },
        'right': {'value': 3, 'left': None, 'right': None}
    }
    print("Expected: 3")
    try:
        print(f"Got: {tree_height(tree)}")
    except TypeError as e:
        print(f"TypeError: {e}")
