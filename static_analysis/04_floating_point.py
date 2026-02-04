"""
Floating Point Pitfalls
=======================
These errors are NOT caught by static analyzers because floating-point
comparisons are syntactically valid, and precision issues are runtime behavior.
"""

import math
import numpy as np


# =============================================================================
# 1. Equality Comparison
# =============================================================================

def check_sum_bad():
    """BAD: Direct equality comparison with floats"""
    result = 0.1 + 0.2
    return result == 0.3  # False!

def check_sum_good():
    """GOOD: Use math.isclose() for float comparison"""
    result = 0.1 + 0.2
    return math.isclose(result, 0.3)  # True

def check_sum_manual():
    """GOOD: Manual epsilon comparison"""
    result = 0.1 + 0.2
    epsilon = 1e-9
    return abs(result - 0.3) < epsilon  # True

# Demo
print("=== Equality Comparison ===")
print(f"0.1 + 0.2 = {0.1 + 0.2}")
print(f"0.1 + 0.2 == 0.3: {check_sum_bad()}")           # False!
print(f"math.isclose(0.1+0.2, 0.3): {check_sum_good()}")  # True
print(f"abs(result - 0.3) < 1e-9: {check_sum_manual()}")  # True


# =============================================================================
# 2. Precision Loss with Large Numbers
# =============================================================================

def precision_loss_demo():
    """Large floats lose precision for small additions"""
    large = 1e16
    result = large + 1 - large
    return result  # Should be 1, but...

# Demo
print("\n=== Precision Loss ===")
print(f"1e16 + 1 - 1e16 = {precision_loss_demo()}")  # 0.0!
print(f"Expected: 1")
print(f"Why: 1e16 can't represent 1e16 + 1 precisely")

# More examples
print(f"\n1e15 + 1 - 1e15 = {1e15 + 1 - 1e15}")  # 1.0 (still works)
print(f"1e16 + 1 - 1e16 = {1e16 + 1 - 1e16}")    # 0.0 (precision lost)
print(f"1e17 + 1 - 1e17 = {1e17 + 1 - 1e17}")    # 0.0


# =============================================================================
# 3. NaN Comparisons
# =============================================================================

def check_nan_bad(value):
    """BAD: Comparing NaN with =="""
    return value == np.nan  # Always False!

def check_nan_good(value):
    """GOOD: Use np.isnan() or math.isnan()"""
    return np.isnan(value)

# Demo
print("\n=== NaN Comparisons ===")
nan_value = np.nan
print(f"np.nan == np.nan: {nan_value == nan_value}")  # False!
print(f"np.isnan(np.nan): {np.isnan(nan_value)}")      # True

# NaN propagates
print(f"\n1 + np.nan = {1 + np.nan}")  # nan
print(f"np.nan > 0: {np.nan > 0}")     # False
print(f"np.nan < 0: {np.nan < 0}")     # False
print(f"np.nan == 0: {np.nan == 0}")   # False


# =============================================================================
# 4. Infinity Comparisons
# =============================================================================

def check_infinity():
    """Infinity behaves somewhat more predictably than NaN"""
    inf = float('inf')
    neg_inf = float('-inf')

    print(f"inf == inf: {inf == inf}")           # True
    print(f"inf > 1e308: {inf > 1e308}")         # True
    print(f"-inf < -1e308: {neg_inf < -1e308}")  # True
    print(f"inf + 1 == inf: {inf + 1 == inf}")   # True
    print(f"inf - inf: {inf - inf}")             # nan!

# Demo
print("\n=== Infinity ===")
check_infinity()


# =============================================================================
# 5. Accumulation Errors
# =============================================================================

def sum_bad():
    """BAD: Naive summation accumulates errors"""
    total = 0.0
    for _ in range(10):
        total += 0.1
    return total

def sum_good():
    """GOOD: Use math.fsum() for accurate summation"""
    return math.fsum([0.1] * 10)

# Demo
print("\n=== Accumulation Errors ===")
naive_sum = sum_bad()
accurate_sum = sum_good()
print(f"Naive sum of 0.1 x 10: {naive_sum}")
print(f"  == 1.0? {naive_sum == 1.0}")  # False!
print(f"math.fsum of 0.1 x 10: {accurate_sum}")
print(f"  == 1.0? {accurate_sum == 1.0}")  # True!


# =============================================================================
# 6. Integer Division Surprises
# =============================================================================

def division_demo():
    """Integer vs float division and large number conversion"""
    # True division always returns float
    print(f"5 / 2 = {5 / 2}")       # 2.5
    print(f"4 / 2 = {4 / 2}")       # 2.0 (float, not int!)

    # Floor division
    print(f"5 // 2 = {5 // 2}")     # 2
    print(f"-5 // 2 = {-5 // 2}")   # -3 (floors toward negative infinity!)

    # Large float to int
    large_float = 1e20
    print(f"\nint(1e20) = {int(large_float)}")  # Works
    print(f"int(1e309) would overflow to inf")  # float('inf') can't become int

# Demo
print("\n=== Integer Division ===")
division_demo()


# =============================================================================
# 7. Comparing Arrays with np.allclose()
# =============================================================================

def compare_arrays_bad():
    """BAD: Using == for array comparison"""
    a = np.array([0.1 + 0.2, 0.3])
    b = np.array([0.3, 0.3])
    return a == b  # Element-wise, not useful for tolerance

def compare_arrays_good():
    """GOOD: Use np.allclose() for array comparison"""
    a = np.array([0.1 + 0.2, 0.3])
    b = np.array([0.3, 0.3])
    return np.allclose(a, b)

# Demo
print("\n=== Array Comparison ===")
a = np.array([0.1 + 0.2, 0.3])
b = np.array([0.3, 0.3])
print(f"a = {a}")
print(f"b = {b}")
print(f"a == b: {a == b}")  # [False  True]
print(f"np.allclose(a, b): {np.allclose(a, b)}")  # True


# =============================================================================
# 8. Relative vs Absolute Tolerance
# =============================================================================

def tolerance_demo():
    """Understanding isclose() parameters"""
    # math.isclose(a, b, rel_tol=1e-9, abs_tol=0.0)
    # Returns True if: abs(a-b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)

    # For numbers near zero, need absolute tolerance
    a = 1e-10
    b = 2e-10

    print(f"a = {a}, b = {b}")
    print(f"isclose(a, b): {math.isclose(a, b)}")  # False (default rel_tol)
    print(f"isclose(a, b, abs_tol=1e-9): {math.isclose(a, b, abs_tol=1e-9)}")  # True

# Demo
print("\n=== Tolerance Types ===")
tolerance_demo()


# =============================================================================
# 9. Decimal for Financial Calculations
# =============================================================================

from decimal import Decimal, ROUND_HALF_UP

def money_bad():
    """BAD: Using float for money"""
    price = 19.99
    quantity = 3
    total = price * quantity
    return total  # 59.97000000000001

def money_good():
    """GOOD: Using Decimal for money"""
    price = Decimal('19.99')
    quantity = 3
    total = price * quantity
    return total  # Decimal('59.97')

# Demo
print("\n=== Financial Calculations ===")
print(f"Float: 19.99 * 3 = {money_bad()}")     # 59.97000000000001
print(f"Decimal: 19.99 * 3 = {money_good()}")  # 59.97


# =============================================================================
# 10. Common Float Gotchas Summary
# =============================================================================

def gotchas_demo():
    """Collection of surprising float behaviors"""
    print("--- Surprising True ---")
    print(f"0.0 == -0.0: {0.0 == -0.0}")                    # True
    print(f"float('inf') == float('inf'): {float('inf') == float('inf')}")  # True

    print("\n--- Surprising False ---")
    print(f"float('nan') == float('nan'): {float('nan') == float('nan')}")  # False
    print(f"0.1 * 3 == 0.3: {0.1 * 3 == 0.3}")              # False

    print("\n--- Surprising Values ---")
    print(f"0.1 + 0.1 + 0.1: {0.1 + 0.1 + 0.1}")            # 0.30000000000000004
    print(f"0.1 * 10: {0.1 * 10}")                          # 1.0 (happens to be exact)
    print(f"sum([0.1] * 10): {sum([0.1] * 10)}")            # 0.9999999999999999

    print("\n--- Type Coercion ---")
    print(f"int(0.9999999999999999): {int(0.9999999999999999)}")  # 0
    print(f"int(1.9999999999999998): {int(1.9999999999999998)}")  # 1
    print(f"round(0.5): {round(0.5)}")                      # 0 (banker's rounding!)
    print(f"round(1.5): {round(1.5)}")                      # 2
    print(f"round(2.5): {round(2.5)}")                      # 2

# Demo
print("\n=== Float Gotchas Summary ===")
gotchas_demo()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("FLOATING POINT CHECKLIST:")
print("=" * 60)
print("1. NEVER use == to compare floats")
print("2. Use math.isclose() or np.isclose() for comparisons")
print("3. Use np.allclose() for array comparisons")
print("4. Use math.isnan() to check for NaN, not ==")
print("5. Use math.fsum() for accurate summation")
print("6. Use Decimal for financial calculations")
print("7. Be aware of precision loss with large numbers")
print("8. Remember: round() uses banker's rounding!")
print("9. Set abs_tol when comparing numbers near zero")
