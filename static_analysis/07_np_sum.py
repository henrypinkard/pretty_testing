"""
np.sum Edge Cases
=================
These errors are NOT caught by static analyzers because they involve
runtime overflow, axis semantics, and dtype behavior.
"""

import numpy as np


# =============================================================================
# 1. Wrong Axis
# =============================================================================

def sum_axis_demo():
    """Understanding axis in np.sum"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])

    print(f"  Array:\n{arr}")
    print(f"  Shape: {arr.shape}")  # (2, 3)

    # No axis: sum all elements
    total = np.sum(arr)
    print(f"\n  np.sum(arr) = {total}")  # 21

    # axis=0: sum ALONG rows (collapse rows)
    col_sums = np.sum(arr, axis=0)
    print(f"  np.sum(arr, axis=0) = {col_sums}")  # [5, 7, 9] - shape (3,)

    # axis=1: sum ALONG columns (collapse columns)
    row_sums = np.sum(arr, axis=1)
    print(f"  np.sum(arr, axis=1) = {row_sums}")  # [6, 15] - shape (2,)

    # Memory aid: the axis you specify is the one that DISAPPEARS

# Demo
print("=== Axis Understanding ===")
sum_axis_demo()


# =============================================================================
# 2. Integer Overflow
# =============================================================================

def overflow_bad():
    """BAD: Integer overflow in sum"""
    # int64 max is about 9.2e18
    large_values = np.array([2**62, 2**62], dtype=np.int64)

    result = np.sum(large_values)
    print(f"  Values: 2^62 + 2^62 = 2^63")
    print(f"  np.sum result: {result}")  # Negative! Overflow!
    print(f"  Expected: {2**63}")

def overflow_good():
    """GOOD: Use float or Python int to avoid overflow"""
    large_values = np.array([2**62, 2**62], dtype=np.int64)

    # Option 1: Specify float dtype
    result1 = np.sum(large_values, dtype=np.float64)
    print(f"  With dtype=float64: {result1}")  # Correct (as float)

    # Option 2: Convert to Python int (arbitrary precision)
    result2 = sum(int(x) for x in large_values)
    print(f"  With Python sum: {result2}")  # Correct

    # Option 3: Use object dtype (slower)
    large_obj = np.array([2**62, 2**62], dtype=object)
    result3 = np.sum(large_obj)
    print(f"  With object dtype: {result3}")  # Correct

# Demo
print("\n=== Integer Overflow ===")
print("BAD:")
overflow_bad()
print("\nGOOD:")
overflow_good()


# =============================================================================
# 3. dtype Not Specified (Small Integers)
# =============================================================================

def dtype_issue():
    """Small int arrays may overflow during sum"""
    # uint8 max is 255
    arr = np.array([200, 200, 200], dtype=np.uint8)

    # NumPy 1.x: sum inherits dtype and overflows
    # NumPy 2.x: sum uses larger dtype by default
    result = np.sum(arr)
    print(f"  Array dtype: {arr.dtype}")
    print(f"  Sum result: {result}")
    print(f"  Sum dtype: {result.dtype}")
    print(f"  Expected: 600")

    # Safe: specify output dtype
    result_safe = np.sum(arr, dtype=np.int32)
    print(f"  With dtype=int32: {result_safe}")

# Demo
print("\n=== dtype Issues ===")
dtype_issue()


# =============================================================================
# 4. keepdims Issues
# =============================================================================

def keepdims_issue():
    """Shape mismatch when keepdims is forgotten"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])  # Shape (2, 3)

    # Without keepdims
    row_sums = np.sum(arr, axis=1)  # Shape (2,)
    print(f"  arr shape: {arr.shape}")
    print(f"  row_sums shape (no keepdims): {row_sums.shape}")

    # Try to normalize rows (divide each row by its sum)
    # This will broadcast incorrectly!
    try:
        normalized_bad = arr / row_sums
        print(f"  arr / row_sums shape: {normalized_bad.shape}")  # (2, 3) but wrong!
        print(f"  Result (WRONG):\n{normalized_bad}")
    except Exception as e:
        print(f"  Error: {e}")

    # With keepdims - correct broadcasting
    row_sums_keep = np.sum(arr, axis=1, keepdims=True)  # Shape (2, 1)
    print(f"\n  row_sums shape (keepdims=True): {row_sums_keep.shape}")
    normalized_good = arr / row_sums_keep
    print(f"  Result (CORRECT):\n{normalized_good}")

# Demo
print("\n=== keepdims ===")
keepdims_issue()


# =============================================================================
# 5. Boolean Sum (Counting True)
# =============================================================================

def bool_sum():
    """np.sum on boolean array counts True values"""
    arr = np.array([1, 2, 3, 4, 5])

    # Count how many elements > 2
    mask = arr > 2
    print(f"  arr = {arr}")
    print(f"  arr > 2 = {mask}")

    # Sum counts True values
    count = np.sum(mask)
    print(f"  np.sum(arr > 2) = {count}")  # 3

    # Equivalent to:
    count2 = np.count_nonzero(arr > 2)
    print(f"  np.count_nonzero(arr > 2) = {count2}")  # 3

# Demo
print("\n=== Boolean Sum ===")
bool_sum()


# =============================================================================
# 6. sum vs nansum
# =============================================================================

def nan_sum():
    """np.sum propagates NaN, np.nansum ignores it"""
    arr = np.array([1, 2, np.nan, 4])

    result1 = np.sum(arr)
    print(f"  arr = {arr}")
    print(f"  np.sum(arr) = {result1}")  # nan

    result2 = np.nansum(arr)
    print(f"  np.nansum(arr) = {result2}")  # 7.0

# Demo
print("\n=== NaN Sum ===")
nan_sum()


# =============================================================================
# 7. Cumulative Sum (cumsum)
# =============================================================================

def cumsum_demo():
    """np.cumsum returns running total"""
    arr = np.array([1, 2, 3, 4])

    # Cumulative sum
    result = np.cumsum(arr)
    print(f"  arr = {arr}")
    print(f"  np.cumsum(arr) = {result}")  # [1, 3, 6, 10]

    # 2D cumsum
    arr2d = np.array([[1, 2, 3],
                      [4, 5, 6]])

    # Flatten first by default
    print(f"\n  2D array:\n{arr2d}")
    print(f"  np.cumsum(arr2d) = {np.cumsum(arr2d)}")  # [1, 3, 6, 10, 15, 21]

    # Along axis
    print(f"  np.cumsum(arr2d, axis=0) =\n{np.cumsum(arr2d, axis=0)}")
    print(f"  np.cumsum(arr2d, axis=1) =\n{np.cumsum(arr2d, axis=1)}")

# Demo
print("\n=== Cumulative Sum ===")
cumsum_demo()


# =============================================================================
# 8. sum on Empty Array
# =============================================================================

def empty_sum():
    """np.sum on empty array returns 0 (not error)"""
    empty = np.array([])

    result = np.sum(empty)
    print(f"  np.sum([]) = {result}")  # 0.0 - no error!
    print(f"  dtype: {result.dtype}")

    # But with specific dtype:
    empty_int = np.array([], dtype=np.int64)
    result_int = np.sum(empty_int)
    print(f"  np.sum([], dtype=int64) = {result_int}")  # 0
    print(f"  dtype: {result_int.dtype}")

# Demo
print("\n=== Empty Array Sum ===")
empty_sum()


# =============================================================================
# 9. Product Instead of Sum
# =============================================================================

def sum_vs_prod():
    """Don't confuse np.sum with np.prod"""
    arr = np.array([1, 2, 3, 4])

    print(f"  arr = {arr}")
    print(f"  np.sum(arr) = {np.sum(arr)}")   # 10 (1+2+3+4)
    print(f"  np.prod(arr) = {np.prod(arr)}")  # 24 (1*2*3*4)

    # Common mistake: using sum when you need product
    # e.g., calculating total array size from shape
    shape = (3, 4, 5)
    total_elements = np.prod(shape)  # NOT np.sum!
    print(f"\n  Shape {shape} has {total_elements} elements")

# Demo
print("\n=== Sum vs Product ===")
sum_vs_prod()


# =============================================================================
# 10. where Parameter
# =============================================================================

def sum_where():
    """Conditional sum using where parameter (NumPy 1.20+)"""
    arr = np.array([1, 2, 3, 4, 5])

    # Sum only elements > 2
    result = np.sum(arr, where=arr > 2)
    print(f"  arr = {arr}")
    print(f"  np.sum(arr, where=arr > 2) = {result}")  # 12 (3+4+5)

    # Alternative: boolean indexing
    result2 = np.sum(arr[arr > 2])
    print(f"  np.sum(arr[arr > 2]) = {result2}")  # 12

# Demo
print("\n=== Conditional Sum ===")
sum_where()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.sum CHECKLIST:")
print("=" * 60)
print("1. axis=0 sums ACROSS rows (result shape = columns)")
print("2. axis=1 sums ACROSS columns (result shape = rows)")
print("3. The axis you specify is the one that DISAPPEARS")
print("4. Use dtype=np.int64 or float64 to prevent overflow")
print("5. Use keepdims=True when broadcasting afterward")
print("6. Use np.nansum() if data may contain NaN")
print("7. np.sum on empty array returns 0, not error")
print("8. np.sum on boolean counts True values")
print("9. Use where= for conditional sums")
print("10. Don't confuse sum with prod!")
