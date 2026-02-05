"""
Wrong Base Case Errors

These functions have a base case, but it returns the wrong value.
The recursion stops, but the final result is incorrect due to
off-by-one errors or incorrect base case values.
"""


def factorial(n):
    """Calculate n! but with wrong base case value.

    Bug: Returns 0 for base case instead of 1.
    Result: Always returns 0 (anything * 0 = 0)
    """
    if n <= 1:
        return 0  # Should be 1
    return n * factorial(n - 1)


# Corrected version:
# def factorial(n):
#     if n <= 1:
#         return 1
#     return n * factorial(n - 1)


def fibonacci(n):
    """Calculate the nth Fibonacci number but with wrong base cases.

    Bug: Base cases are swapped (fib(0) should be 0, fib(1) should be 1).
    Result: Off-by-one in the sequence
    """
    if n == 0:
        return 1  # Should be 0
    if n == 1:
        return 0  # Should be 1
    return fibonacci(n - 1) + fibonacci(n - 2)


# Corrected version:
# def fibonacci(n):
#     if n == 0:
#         return 0
#     if n == 1:
#         return 1
#     return fibonacci(n - 1) + fibonacci(n - 2)


def power(base, exp):
    """Calculate base^exp but with wrong base case.

    Bug: Returns 0 when exp is 0, but x^0 = 1 for any x.
    Result: Always returns 0
    """
    if exp == 0:
        return 0  # Should be 1
    return base * power(base, exp - 1)


# Corrected version:
# def power(base, exp):
#     if exp == 0:
#         return 1
#     return base * power(base, exp - 1)


def count_digits(n):
    """Count digits in a number but with wrong base case.

    Bug: Returns 0 for single digit, should return 1.
    Result: Always one less than the correct count
    """
    if n < 10:
        return 0  # Should be 1
    return 1 + count_digits(n // 10)


# Corrected version:
# def count_digits(n):
#     if n < 10:
#         return 1
#     return 1 + count_digits(n // 10)


if __name__ == "__main__":
    print("Testing factorial(5)...")
    print("Expected: 120")
    print(f"Got: {factorial(5)}")

    print("\nTesting fibonacci for n=0 to 6...")
    print("Expected: 0, 1, 1, 2, 3, 5, 8")
    print("Got:     ", ", ".join(str(fibonacci(i)) for i in range(7)))

    print("\nTesting power(2, 3)...")
    print("Expected: 8")
    print(f"Got: {power(2, 3)}")

    print("\nTesting count_digits(12345)...")
    print("Expected: 5")
    print(f"Got: {count_digits(12345)}")
