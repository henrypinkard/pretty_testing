"""
Not Reducing Toward Base Case Errors

These functions have a base case, but the recursive call doesn't
make progress toward it. The argument stays the same or moves
in the wrong direction.
"""


def find_element(lst, target, index=0):
    """Find target in list but index never changes.

    Bug: Passes 'index' instead of 'index + 1' in recursive call.
    Result: Infinite recursion, always checking the same element
    """
    if index >= len(lst):
        return -1
    if lst[index] == target:
        return index
    return find_element(lst, target, index)  # Should be index + 1


# Corrected version:
# def find_element(lst, target, index=0):
#     if index >= len(lst):
#         return -1
#     if lst[index] == target:
#         return index
#     return find_element(lst, target, index + 1)


def reverse_string(s):
    """Reverse a string but forgot to slice.

    Bug: Passes entire string 's' instead of 's[:-1]' or 's[1:]'.
    Result: Infinite recursion with the same string
    """
    if len(s) <= 1:
        return s
    return s[-1] + reverse_string(s)  # Should be s[:-1]


# Corrected version:
# def reverse_string(s):
#     if len(s) <= 1:
#         return s
#     return s[-1] + reverse_string(s[:-1])


def gcd(a, b):
    """Calculate GCD but arguments don't reduce.

    Bug: Passes 'a' instead of 'b' as first argument.
    Result: Infinite recursion with same values
    """
    if b == 0:
        return a
    return gcd(a, a % b)  # Should be gcd(b, a % b)


# Corrected version:
# def gcd(a, b):
#     if b == 0:
#         return a
#     return gcd(b, a % b)


def binary_search(arr, target, low, high):
    """Binary search but mid calculation doesn't update bounds correctly.

    Bug: Recursive calls don't exclude mid from the search range.
    Result: Infinite loop when target is not in array
    """
    if low > high:
        return -1

    mid = (low + high) // 2

    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        return binary_search(arr, target, mid, high)  # Should be mid + 1
    else:
        return binary_search(arr, target, low, mid)   # Should be mid - 1


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


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(50)  # Lower limit to fail faster

    print("Testing find_element([1, 2, 3, 4, 5], 3)...")
    print("Expected: 2")
    try:
        result = find_element([1, 2, 3, 4, 5], 3)
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting reverse_string('hello')...")
    print("Expected: 'olleh'")
    try:
        result = reverse_string("hello")
        print(f"Got: '{result}'")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting gcd(48, 18)...")
    print("Expected: 6")
    try:
        result = gcd(48, 18)
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting binary_search([1,2,3,4,5,6,7], 8, 0, 6)...")
    print("Expected: -1 (not found)")
    try:
        result = binary_search([1, 2, 3, 4, 5, 6, 7], 8, 0, 6)
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")
