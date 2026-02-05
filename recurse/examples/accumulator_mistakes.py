"""
Accumulator Pattern Mistakes

These functions use an accumulator to build results during recursion,
but make common mistakes: forgetting to pass it, resetting it each call,
or using the wrong initial value.
"""


def factorial_acc(n, acc):
    """Factorial with accumulator but forgot to pass accumulator.

    Bug: Recursive call doesn't pass the accumulator.
    Result: TypeError - missing required argument
    """
    if n <= 1:
        return acc

    # Wrong: forgot to pass acc * n
    return factorial_acc(n - 1)


# Corrected version:
# def factorial_acc(n, acc=1):
#     if n <= 1:
#         return acc
#     return factorial_acc(n - 1, acc * n)


def sum_list_acc(lst, acc=0):
    """Sum list with accumulator but resets accumulator each call.

    Bug: Creates new acc = 0 instead of using the passed value correctly.
    Result: Only returns the last element
    """
    if not lst:
        return acc

    acc = 0  # Wrong: resets accumulator!
    acc += lst[0]
    return sum_list_acc(lst[1:], acc)


# Corrected version:
# def sum_list_acc(lst, acc=0):
#     if not lst:
#         return acc
#     return sum_list_acc(lst[1:], acc + lst[0])


def reverse_string_acc(s, acc=""):
    """Reverse string with accumulator but wrong initial value.

    Bug: Initial accumulator has a space, corrupting the result.
    Result: Reversed string with extra space at the end
    """
    if not s:
        return acc

    return reverse_string_acc(s[1:], s[0] + acc)


def test_reverse():
    # The bug is actually in how we call it:
    # Calling with wrong initial value
    return reverse_string_acc("hello", " ")  # Wrong initial value!


# Corrected version:
# def reverse_string_acc(s, acc=""):
#     if not s:
#         return acc
#     return reverse_string_acc(s[1:], s[0] + acc)
# # Called with: reverse_string_acc("hello") or reverse_string_acc("hello", "")


def count_evens_acc(lst, acc=1):
    """Count even numbers but wrong initial accumulator.

    Bug: Starts with acc=1 instead of acc=0.
    Result: Count is always one too high
    """
    if not lst:
        return acc

    if lst[0] % 2 == 0:
        return count_evens_acc(lst[1:], acc + 1)
    return count_evens_acc(lst[1:], acc)


# Corrected version:
# def count_evens_acc(lst, acc=0):
#     if not lst:
#         return acc
#     if lst[0] % 2 == 0:
#         return count_evens_acc(lst[1:], acc + 1)
#     return count_evens_acc(lst[1:], acc)


def collect_positives_acc(lst, acc=[]):
    """Collect positive numbers but mutable default accumulator.

    Bug: Default mutable list accumulates across calls.
    Result: Results from previous calls persist
    """
    if not lst:
        return acc

    if lst[0] > 0:
        acc.append(lst[0])

    return collect_positives_acc(lst[1:], acc)


# Corrected version:
# def collect_positives_acc(lst, acc=None):
#     if acc is None:
#         acc = []
#     if not lst:
#         return acc
#     if lst[0] > 0:
#         acc.append(lst[0])
#     return collect_positives_acc(lst[1:], acc)


def join_strings_acc(strings, separator, acc=None):
    """Join strings with separator but accumulator logic is wrong.

    Bug: Adds separator at the wrong position (before first element).
    Result: Output starts with separator
    """
    if acc is None:
        acc = ""

    if not strings:
        return acc

    # Wrong: always adds separator, even for first element
    acc = acc + separator + strings[0]
    return join_strings_acc(strings[1:], separator, acc)


# Corrected version:
# def join_strings_acc(strings, separator, acc=None):
#     if not strings:
#         return acc if acc is not None else ""
#     if acc is None:
#         return join_strings_acc(strings[1:], separator, strings[0])
#     return join_strings_acc(strings[1:], separator, acc + separator + strings[0])


if __name__ == "__main__":
    print("Testing factorial_acc(5, 1)...")
    print("Expected: 120")
    try:
        result = factorial_acc(5, 1)
        print(f"Got: {result}")
    except TypeError as e:
        print(f"TypeError: {e}")

    print("\nTesting sum_list_acc([1, 2, 3, 4, 5])...")
    print("Expected: 15")
    print(f"Got: {sum_list_acc([1, 2, 3, 4, 5])}")

    print("\nTesting reverse with wrong initial value...")
    print("Expected: 'olleh'")
    print(f"Got: '{test_reverse()}'")

    print("\nTesting count_evens_acc([1, 2, 3, 4, 5, 6])...")
    print("Expected: 3")
    print(f"Got: {count_evens_acc([1, 2, 3, 4, 5, 6])}")

    print("\nTesting collect_positives_acc multiple times...")
    print("First call with [-1, 2, -3, 4]:")
    result1 = collect_positives_acc([-1, 2, -3, 4])
    print(f"Got: {result1}")
    print("Second call with [5, -6, 7]:")
    result2 = collect_positives_acc([5, -6, 7])
    print("Expected: [5, 7]")
    print(f"Got: {result2}")

    print("\nTesting join_strings_acc(['a', 'b', 'c'], '-')...")
    print("Expected: 'a-b-c'")
    print(f"Got: '{join_strings_acc(['a', 'b', 'c'], '-')}'")
