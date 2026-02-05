"""
Missing Base Case Errors

These functions recurse forever because they lack a stopping condition.
This is one of the most common recursion bugs - the function never knows
when to stop calling itself.
"""


def factorial(n):
    """Calculate n! but missing the base case.

    Bug: No base case to stop recursion when n reaches 0 or 1.
    Result: RecursionError (maximum recursion depth exceeded)
    """
    return n * factorial(n - 1)


# Corrected version:
# def factorial(n):
#     if n <= 1:
#         return 1
#     return n * factorial(n - 1)


def sum_list(lst):
    """Sum all elements in a list but missing the base case.

    Bug: No check for empty list, so it recurses forever.
    Result: RecursionError (maximum recursion depth exceeded)
    """
    return lst[0] + sum_list(lst[1:])


# Corrected version:
# def sum_list(lst):
#     if not lst:
#         return 0
#     return lst[0] + sum_list(lst[1:])


def count_down(n):
    """Print numbers counting down but missing the base case.

    Bug: Never stops printing and calling itself.
    Result: RecursionError (maximum recursion depth exceeded)
    """
    print(n)
    count_down(n - 1)


# Corrected version:
# def count_down(n):
#     if n < 0:
#         return
#     print(n)
#     count_down(n - 1)


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(50)  # Lower limit to fail faster

    print("Testing factorial(5)...")
    print("Expected: 120")
    try:
        result = factorial(5)
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting sum_list([1, 2, 3, 4, 5])...")
    print("Expected: 15")
    try:
        result = sum_list([1, 2, 3, 4, 5])
        print(f"Got: {result}")
    except (RecursionError, IndexError) as e:
        print(f"{type(e).__name__}: {e}")

    print("\nTesting count_down(3)...")
    print("Expected: 3, 2, 1, 0")
    try:
        count_down(3)
    except RecursionError as e:
        print(f"RecursionError: {e}")
