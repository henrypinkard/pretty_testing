"""
np.min / np.max Pitfalls
========================
These errors are NOT caught by static analyzers because they involve
runtime values and axis semantics.
"""

import numpy as np


# =============================================================================
# 1. Wrong Axis
# =============================================================================

def find_min_bad():
    """BAD: Using wrong axis"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])

    # axis=0 reduces ALONG rows (result has shape of columns)
    # axis=1 reduces ALONG columns (result has shape of rows)

    result = np.min(arr, axis=0)  # Min of each column: [1, 2, 3]
    print(f"  axis=0 (min per column): {result}")

    result = np.min(arr, axis=1)  # Min of each row: [1, 4]
    print(f"  axis=1 (min per row): {result}")

    # Common mistake: confusing which axis is which
    # axis=0 operates ACROSS rows (vertically)
    # axis=1 operates ACROSS columns (horizontally)

def find_min_good():
    """GOOD: Be explicit about what you want"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])

    # Want minimum in each row? That's axis=1
    row_mins = np.min(arr, axis=1)
    print(f"  Row minimums: {row_mins}")  # [1, 4]

    # Want minimum in each column? That's axis=0
    col_mins = np.min(arr, axis=0)
    print(f"  Column minimums: {col_mins}")  # [1, 2, 3]

    # Want global minimum? No axis
    global_min = np.min(arr)
    print(f"  Global minimum: {global_min}")  # 1

# Demo
print("=== Wrong Axis ===")
print("Array:\n[[1, 2, 3],\n [4, 5, 6]]")
print("\nResults:")
find_min_bad()
print("\nClear labeling:")
find_min_good()


# =============================================================================
# 2. Empty Array
# =============================================================================

def min_empty_bad():
    """BAD: np.min on empty array raises ValueError"""
    empty = np.array([])
    try:
        result = np.min(empty)  # ValueError!
    except ValueError as e:
        print(f"  ValueError: {e}")
    return None

def min_empty_good():
    """GOOD: Check for empty or use initial value"""
    empty = np.array([])

    # Option 1: Check first
    if empty.size == 0:
        result = float('inf')  # Or some default
        print(f"  Check empty first: {result}")
    else:
        result = np.min(empty)

    # Option 2: Use initial (NumPy 1.22+)
    result = np.min(empty, initial=float('inf'))
    print(f"  With initial=inf: {result}")

    return result

# Demo
print("\n=== Empty Array ===")
print("BAD:")
min_empty_bad()
print("GOOD:")
min_empty_good()


# =============================================================================
# 3. Python min/max vs NumPy
# =============================================================================

def compare_minmax():
    """Different behavior between Python and NumPy min/max"""
    arr1 = np.array([1, 2, 3])
    arr2 = np.array([4, 0, 2])

    # Python built-in min with single array - works but slower
    py_min = min(arr1)
    np_min = np.min(arr1)
    print(f"  min(arr1) = {py_min}")      # 1
    print(f"  np.min(arr1) = {np_min}")   # 1

    # Python min with two arrays - compares element-wise!
    py_min2 = min(arr1, arr2)  # Compares arrays, doesn't do element-wise
    print(f"  min(arr1, arr2) type: {type(py_min2)}")  # numpy.ndarray

    # For element-wise minimum, use np.minimum
    np_min2 = np.minimum(arr1, arr2)
    print(f"  np.minimum(arr1, arr2) = {np_min2}")  # [1, 0, 2]

# Demo
print("\n=== Python vs NumPy min/max ===")
print("arr1 = [1, 2, 3], arr2 = [4, 0, 2]")
compare_minmax()


# =============================================================================
# 4. keepdims Forgotten
# =============================================================================

def keepdims_bad():
    """BAD: Shape changes unexpectedly without keepdims"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])

    row_mins = np.min(arr, axis=1)  # Shape (2,) - lost a dimension!
    print(f"  arr shape: {arr.shape}")
    print(f"  row_mins shape: {row_mins.shape}")  # (2,) not (2, 1)

    # This fails for broadcasting in subsequent operations
    try:
        # Want to subtract row min from each element
        result = arr - row_mins  # Broadcasting error or wrong result
        print(f"  arr - row_mins shape: {result.shape}")
    except Exception as e:
        print(f"  Error: {e}")

def keepdims_good():
    """GOOD: Use keepdims=True to preserve dimensions"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])

    row_mins = np.min(arr, axis=1, keepdims=True)  # Shape (2, 1)
    print(f"  arr shape: {arr.shape}")
    print(f"  row_mins shape: {row_mins.shape}")  # (2, 1)

    # Now broadcasting works correctly
    result = arr - row_mins
    print(f"  arr - row_mins:\n{result}")

# Demo
print("\n=== keepdims ===")
print("Array:\n[[1, 2, 3],\n [4, 5, 6]]")
print("\nBAD (without keepdims):")
keepdims_bad()
print("\nGOOD (with keepdims=True):")
keepdims_good()


# =============================================================================
# 5. NaN Handling
# =============================================================================

def nan_handling_bad():
    """BAD: np.min/max return nan if any element is nan"""
    arr = np.array([1, np.nan, 2, 3])

    result = np.min(arr)
    print(f"  np.min([1, nan, 2, 3]) = {result}")  # nan!

    result = np.max(arr)
    print(f"  np.max([1, nan, 2, 3]) = {result}")  # nan!

def nan_handling_good():
    """GOOD: Use np.nanmin/np.nanmax to ignore NaN"""
    arr = np.array([1, np.nan, 2, 3])

    result = np.nanmin(arr)
    print(f"  np.nanmin([1, nan, 2, 3]) = {result}")  # 1

    result = np.nanmax(arr)
    print(f"  np.nanmax([1, nan, 2, 3]) = {result}")  # 3

# Demo
print("\n=== NaN Handling ===")
print("BAD (nan propagates):")
nan_handling_bad()
print("GOOD (ignore nan):")
nan_handling_good()


# =============================================================================
# 6. argmin/argmax Returns First Occurrence
# =============================================================================

def argmin_demo():
    """argmin/argmax return FIRST index if there are ties"""
    arr = np.array([1, 3, 1, 2, 1])  # Multiple minimums

    idx = np.argmin(arr)
    print(f"  arr = {arr}")
    print(f"  np.argmin(arr) = {idx}")  # 0 (first occurrence)

    # To get ALL indices of minimum:
    min_val = np.min(arr)
    all_min_idx = np.where(arr == min_val)[0]
    print(f"  All min indices: {all_min_idx}")  # [0, 2, 4]

# Demo
print("\n=== argmin/argmax Ties ===")
argmin_demo()


# =============================================================================
# 7. Multi-dimensional argmin/argmax
# =============================================================================

def argmin_2d_demo():
    """argmin on 2D array returns flat index or axis index"""
    arr = np.array([[5, 2, 8],
                    [1, 9, 3]])

    # Without axis: returns FLAT index
    flat_idx = np.argmin(arr)
    print(f"  np.argmin(arr) = {flat_idx}")  # 3 (flat index of 1)

    # To get 2D indices:
    idx_2d = np.unravel_index(flat_idx, arr.shape)
    print(f"  2D index: {idx_2d}")  # (1, 0)
    print(f"  Value at that index: {arr[idx_2d]}")  # 1

    # With axis: returns indices along that axis
    row_argmin = np.argmin(arr, axis=1)
    print(f"  np.argmin(arr, axis=1) = {row_argmin}")  # [1, 0] (index of min in each row)

    col_argmin = np.argmin(arr, axis=0)
    print(f"  np.argmin(arr, axis=0) = {col_argmin}")  # [1, 0, 1] (index of min in each col)

# Demo
print("\n=== Multi-dimensional argmin ===")
print("Array:\n[[5, 2, 8],\n [1, 9, 3]]")
argmin_2d_demo()


# =============================================================================
# 8. Comparing np.amax vs np.max vs ndarray.max
# =============================================================================

def compare_max_functions():
    """All equivalent, but different namespaces"""
    arr = np.array([1, 2, 3])

    # All these do the same thing:
    r1 = np.max(arr)
    r2 = np.amax(arr)
    r3 = arr.max()

    print(f"  np.max(arr) = {r1}")
    print(f"  np.amax(arr) = {r2}")  # 'a' for array
    print(f"  arr.max() = {r3}")

    # np.maximum is DIFFERENT - element-wise max of two arrays
    arr2 = np.array([0, 5, 2])
    r4 = np.maximum(arr, arr2)
    print(f"  np.maximum([1,2,3], [0,5,2]) = {r4}")  # [1, 5, 3]

# Demo
print("\n=== max Function Variants ===")
compare_max_functions()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.min/np.max CHECKLIST:")
print("=" * 60)
print("1. axis=0 reduces ACROSS rows (result shape = columns)")
print("2. axis=1 reduces ACROSS columns (result shape = rows)")
print("3. Check for empty arrays before calling min/max")
print("4. Use keepdims=True when broadcasting afterward")
print("5. Use np.nanmin/np.nanmax if data may contain NaN")
print("6. Use np.minimum/np.maximum for element-wise comparison")
print("7. argmin/argmax return FIRST occurrence of ties")
print("8. Use np.unravel_index for 2D position from flat argmin")
