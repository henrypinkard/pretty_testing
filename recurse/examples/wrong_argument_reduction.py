"""
Wrong Argument Reduction Errors

These functions reduce the argument in the wrong way - wrong direction,
wrong amount, or wrong slice. The recursion terminates but produces
incorrect results due to processing the wrong portion of data.
"""


def reverse_list(lst):
    """Reverse a list but slicing in wrong direction.

    Bug: Takes first element instead of last, and wrong slice.
    Result: Returns list in original order (or infinite recursion)
    """
    if len(lst) <= 1:
        return lst

    # Wrong: should be [lst[-1]] + reverse_list(lst[:-1])
    return [lst[0]] + reverse_list(lst[1:])


# Corrected version:
# def reverse_list(lst):
#     if len(lst) <= 1:
#         return lst
#     return [lst[-1]] + reverse_list(lst[:-1])


def sum_digits(n):
    """Sum all digits of a number but wrong reduction.

    Bug: Uses n % 100 instead of n // 10, skips digits.
    Result: Wrong sum, misses some digits
    """
    if n < 10:
        return n

    # Wrong: n % 100 doesn't reduce properly
    return (n % 10) + sum_digits(n % 100)


# Corrected version:
# def sum_digits(n):
#     if n < 10:
#         return n
#     return (n % 10) + sum_digits(n // 10)


def find_min_index(lst, start=0):
    """Find index of minimum element but off-by-one in recursion.

    Bug: Passes start instead of start + 1.
    Result: Infinite recursion
    """
    if start == len(lst) - 1:
        return start

    # Wrong: should be start + 1
    min_rest = find_min_index(lst, start)

    if lst[start] < lst[min_rest]:
        return start
    return min_rest


# Corrected version:
# def find_min_index(lst, start=0):
#     if start == len(lst) - 1:
#         return start
#     min_rest = find_min_index(lst, start + 1)
#     if lst[start] < lst[min_rest]:
#         return start
#     return min_rest


def string_length(s):
    """Calculate string length but wrong slice.

    Bug: Uses s[2:] instead of s[1:], counts half the characters.
    Result: Returns approximately half the actual length
    """
    if s == "":
        return 0

    # Wrong: skips 2 characters at a time
    return 1 + string_length(s[2:])


# Corrected version:
# def string_length(s):
#     if s == "":
#         return 0
#     return 1 + string_length(s[1:])


def power_of_two(n):
    """Check if n is a power of 2 using recursion, but wrong reduction.

    Bug: Divides by 3 instead of 2.
    Result: Wrong answer for most inputs
    """
    if n == 1:
        return True
    if n <= 0 or n % 2 != 0:
        return False

    # Wrong: should divide by 2
    return power_of_two(n // 3)


# Corrected version:
# def power_of_two(n):
#     if n == 1:
#         return True
#     if n <= 0 or n % 2 != 0:
#         return False
#     return power_of_two(n // 2)


def nth_element(lst, n):
    """Get nth element by recursion but wrong index reduction.

    Bug: Decrements n by 2 instead of 1.
    Result: Returns wrong element or index error
    """
    if n == 0:
        return lst[0]

    # Wrong: should be n - 1
    return nth_element(lst[1:], n - 2)


# Corrected version:
# def nth_element(lst, n):
#     if n == 0:
#         return lst[0]
#     return nth_element(lst[1:], n - 1)


if __name__ == "__main__":
    import sys
    sys.setrecursionlimit(50)

    print("Testing reverse_list([1, 2, 3, 4, 5])...")
    print("Expected: [5, 4, 3, 2, 1]")
    print(f"Got: {reverse_list([1, 2, 3, 4, 5])}")

    print("\nTesting sum_digits(12345)...")
    print("Expected: 15 (1+2+3+4+5)")
    try:
        print(f"Got: {sum_digits(12345)}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting find_min_index([3, 1, 4, 1, 5])...")
    print("Expected: 1")
    try:
        result = find_min_index([3, 1, 4, 1, 5])
        print(f"Got: {result}")
    except RecursionError as e:
        print(f"RecursionError: {e}")

    print("\nTesting string_length('hello')...")
    print("Expected: 5")
    print(f"Got: {string_length('hello')}")

    print("\nTesting power_of_two(8)...")
    print("Expected: True")
    print(f"Got: {power_of_two(8)}")

    print("\nTesting nth_element([10, 20, 30, 40, 50], 3)...")
    print("Expected: 40")
    try:
        result = nth_element([10, 20, 30, 40, 50], 3)
        print(f"Got: {result}")
    except (IndexError, RecursionError) as e:
        print(f"Error: {e}")
