"""
np.where: 1-arg vs 3-arg Confusion
==================================
These errors are NOT caught by static analyzers because both forms are valid,
but they do completely different things.
"""

import numpy as np


# =============================================================================
# The Two Forms of np.where
# =============================================================================
print("=== THE TWO FORMS OF np.where ===")
print()
print("1-arg form: np.where(condition)")
print("   -> Returns TUPLE of indices (same as np.nonzero)")
print()
print("3-arg form: np.where(condition, x, y)")
print("   -> Returns ARRAY with x where True, y where False")
print()


# =============================================================================
# 1. One-Argument Form (Same as nonzero)
# =============================================================================

def where_1arg():
    """1-arg np.where is equivalent to np.nonzero"""
    arr = np.array([0, 1, 0, 2, 0, 3])

    # 1-arg: returns tuple of indices
    result = np.where(arr > 0)
    print(f"  arr = {arr}")
    print(f"  np.where(arr > 0) = {result}")
    print(f"  Type: {type(result)}")  # tuple
    print(f"  Indices: {result[0]}")  # [1, 3, 5]

    # Same as nonzero
    result2 = np.nonzero(arr > 0)
    print(f"  np.nonzero(arr > 0) = {result2}")  # Same!

# Demo
print("=== 1-Argument Form ===")
where_1arg()


# =============================================================================
# 2. Three-Argument Form (Conditional Selection)
# =============================================================================

def where_3arg():
    """3-arg np.where selects values based on condition"""
    arr = np.array([1, 2, 3, 4, 5])

    # 3-arg: returns array with conditional values
    result = np.where(arr > 3, arr, 0)  # Where > 3, keep arr; else 0
    print(f"  arr = {arr}")
    print(f"  np.where(arr > 3, arr, 0) = {result}")  # [0, 0, 0, 4, 5]
    print(f"  Type: {type(result)}")  # ndarray

    # Think of it as: if condition else
    # result[i] = arr[i] if arr[i] > 3 else 0

# Demo
print("\n=== 3-Argument Form ===")
where_3arg()


# =============================================================================
# 3. Common Confusion
# =============================================================================

def confusion_demo():
    """The #1 mistake: expecting 1-arg to return values"""
    arr = np.array([10, 20, 30, 40, 50])

    print(f"  arr = {arr}")
    print(f"  Goal: Get values greater than 25")

    # WRONG: 1-arg returns indices, not values!
    result_wrong = np.where(arr > 25)
    print(f"\n  WRONG: np.where(arr > 25) = {result_wrong}")
    print(f"  This is a tuple of indices, not values!")

    # RIGHT: Use 3-arg or boolean indexing
    result_right1 = np.where(arr > 25, arr, np.nan)
    print(f"\n  3-arg: np.where(arr > 25, arr, nan) = {result_right1}")

    result_right2 = arr[arr > 25]
    print(f"  Boolean indexing: arr[arr > 25] = {result_right2}")

    result_right3 = arr[np.where(arr > 25)]
    print(f"  Indexing with where: arr[np.where(arr > 25)] = {result_right3}")

# Demo
print("\n=== Common Confusion ===")
confusion_demo()


# =============================================================================
# 4. Broadcasting in 3-arg Form
# =============================================================================

def where_broadcasting_bad():
    """BAD: Shape mismatch in 3-arg where"""
    condition = np.array([True, False, True])
    x = np.array([1, 2])  # Wrong shape!
    y = np.array([10, 20, 30])

    try:
        result = np.where(condition, x, y)  # ValueError!
    except ValueError as e:
        print(f"  ValueError: {e}")

def where_broadcasting_good():
    """GOOD: All arrays must broadcast together"""
    condition = np.array([True, False, True])
    x = np.array([1, 2, 3])
    y = np.array([10, 20, 30])

    result = np.where(condition, x, y)
    print(f"  condition = {condition}")
    print(f"  x = {x}")
    print(f"  y = {y}")
    print(f"  result = {result}")  # [1, 20, 3]

    # Scalars broadcast fine
    result2 = np.where(condition, 1, 0)
    print(f"  np.where(condition, 1, 0) = {result2}")  # [1, 0, 1]

# Demo
print("\n=== Broadcasting ===")
print("BAD (shape mismatch):")
where_broadcasting_bad()
print("\nGOOD:")
where_broadcasting_good()


# =============================================================================
# 5. Type Coercion in 3-arg Form
# =============================================================================

def where_type_coercion():
    """3-arg where coerces types to common type"""
    condition = np.array([True, False, True])

    # int + float -> float
    result1 = np.where(condition, 1, 1.5)
    print(f"  np.where(cond, 1, 1.5) dtype: {result1.dtype}")  # float64
    print(f"  values: {result1}")  # [1.0, 1.5, 1.0]

    # int + str -> object (or error in some versions)
    # This is often a mistake
    result2 = np.where(condition, 1, "zero")
    print(f"  np.where(cond, 1, 'zero') dtype: {result2.dtype}")  # <U21 or object
    print(f"  values: {result2}")  # ['1', 'zero', '1'] - integers become strings!

# Demo
print("\n=== Type Coercion ===")
where_type_coercion()


# =============================================================================
# 6. 2D Array Examples
# =============================================================================

def where_2d():
    """np.where with 2D arrays"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6],
                    [7, 8, 9]])

    print(f"  Array:\n{arr}")

    # 1-arg form: returns (row_indices, col_indices)
    result1 = np.where(arr > 5)
    print(f"\n  1-arg: np.where(arr > 5) = {result1}")
    print(f"  Row indices: {result1[0]}")
    print(f"  Col indices: {result1[1]}")
    print(f"  Values: {arr[result1]}")  # [6, 7, 8, 9]

    # 3-arg form: element-wise conditional
    result2 = np.where(arr > 5, arr, 0)
    print(f"\n  3-arg: np.where(arr > 5, arr, 0) =\n{result2}")

# Demo
print("\n=== 2D Arrays ===")
where_2d()


# =============================================================================
# 7. Nested Conditions
# =============================================================================

def nested_conditions():
    """Multiple conditions with where"""
    arr = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])

    # Nested where for multiple conditions
    # Like: if x < 3: 'low' elif x < 7: 'med' else: 'high'
    result = np.where(arr < 3, 'low',
                      np.where(arr < 7, 'med', 'high'))

    print(f"  arr = {arr}")
    print(f"  Categories: {result}")

    # Alternative: np.select for cleaner syntax
    conditions = [arr < 3, arr < 7, arr >= 7]
    choices = ['low', 'med', 'high']
    result2 = np.select(conditions, choices)
    print(f"  np.select result: {result2}")

# Demo
print("\n=== Nested Conditions ===")
nested_conditions()


# =============================================================================
# 8. Common Patterns
# =============================================================================

def common_patterns():
    """Common use cases for np.where"""
    arr = np.array([-2, -1, 0, 1, 2])

    print(f"  arr = {arr}")

    # Pattern 1: Replace negative values
    result1 = np.where(arr < 0, 0, arr)
    print(f"  Replace negatives with 0: {result1}")

    # Pattern 2: Clip values (like np.clip)
    result2 = np.where(arr < -1, -1, np.where(arr > 1, 1, arr))
    print(f"  Clip to [-1, 1]: {result2}")

    # Pattern 3: Sign function
    result3 = np.where(arr > 0, 1, np.where(arr < 0, -1, 0))
    print(f"  Sign: {result3}")

    # Better: use np.sign
    print(f"  np.sign: {np.sign(arr)}")

    # Pattern 4: Fill NaN
    arr_nan = np.array([1, np.nan, 3, np.nan, 5])
    result4 = np.where(np.isnan(arr_nan), 0, arr_nan)
    print(f"\n  Fill NaN with 0: {result4}")

# Demo
print("\n=== Common Patterns ===")
common_patterns()


# =============================================================================
# 9. Performance Note
# =============================================================================

def performance_note():
    """np.where evaluates BOTH branches"""
    arr = np.array([1, 2, 0, 4, 0])

    # This will show a warning because it divides by zero
    # EVEN THOUGH we're trying to handle zero!
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # Suppress for demo

        # BAD: Both 1/arr and 0 are evaluated before where picks
        result = np.where(arr != 0, 1/arr, 0)
        print(f"  arr = {arr}")
        print(f"  np.where(arr != 0, 1/arr, 0) = {result}")

    # Better for avoiding division by zero:
    result2 = np.zeros_like(arr, dtype=float)
    mask = arr != 0
    result2[mask] = 1 / arr[mask]
    print(f"  Safe division: {result2}")

# Demo
print("\n=== Performance Note ===")
print("Note: np.where evaluates BOTH x and y before selecting!")
performance_note()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.where CHECKLIST:")
print("=" * 60)
print("1. 1-arg form: np.where(cond) returns TUPLE of indices")
print("2. 3-arg form: np.where(cond, x, y) returns ARRAY of values")
print("3. 1-arg is same as np.nonzero()")
print("4. To get values: arr[np.where(cond)] or arr[cond]")
print("5. In 3-arg form: condition, x, y must broadcast together")
print("6. Result dtype is common type of x and y")
print("7. BOTH x and y are fully evaluated (no short-circuit)")
print("8. Use np.select() for multiple conditions")
print("9. Boolean indexing is often simpler: arr[arr > 0]")
