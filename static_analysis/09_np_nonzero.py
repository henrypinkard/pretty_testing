"""
np.nonzero Return Format
========================
These errors are NOT caught by static analyzers because indexing into
tuples is valid Python, but the logic may be wrong.
"""

import numpy as np


# =============================================================================
# 1. Returns Tuple of Arrays
# =============================================================================

def nonzero_basic():
    """nonzero returns a TUPLE of arrays, even for 1D"""
    arr = np.array([0, 1, 0, 2, 0, 3])

    result = np.nonzero(arr)
    print(f"  arr = {arr}")
    print(f"  np.nonzero(arr) = {result}")
    print(f"  Type: {type(result)}")  # <class 'tuple'>
    print(f"  Length: {len(result)}")  # 1 (for 1D array)

    # The actual indices are inside the tuple
    indices = result[0]
    print(f"  indices = result[0] = {indices}")  # [1, 3, 5]

# Demo
print("=== nonzero Returns Tuple ===")
nonzero_basic()


# =============================================================================
# 2. Indexing Confusion
# =============================================================================

def indexing_bad():
    """BAD: Confusing indices with values"""
    arr = np.array([0, 5, 0, 10, 0, 15])

    result = np.nonzero(arr)

    # This gives indices, NOT values!
    print(f"  arr = {arr}")
    print(f"  np.nonzero(arr)[0] = {result[0]}")  # [1, 3, 5] - indices!
    print(f"  (These are positions, not values)")

def indexing_good():
    """GOOD: Get values using indices"""
    arr = np.array([0, 5, 0, 10, 0, 15])

    # Get indices
    indices = np.nonzero(arr)[0]

    # Get values using indices
    values = arr[indices]
    print(f"  arr = {arr}")
    print(f"  indices: {indices}")  # [1, 3, 5]
    print(f"  values: {values}")    # [5, 10, 15]

    # Or more directly:
    values2 = arr[np.nonzero(arr)]
    print(f"  arr[np.nonzero(arr)] = {values2}")  # [5, 10, 15]

    # Or even simpler:
    values3 = arr[arr != 0]
    print(f"  arr[arr != 0] = {values3}")  # [5, 10, 15]

# Demo
print("\n=== Indexing Confusion ===")
print("BAD (getting indices instead of values):")
indexing_bad()
print("\nGOOD (getting actual values):")
indexing_good()


# =============================================================================
# 3. Multi-dimensional Arrays
# =============================================================================

def nonzero_2d():
    """2D arrays return (row_indices, col_indices)"""
    arr = np.array([[0, 1, 0],
                    [2, 0, 3],
                    [0, 4, 0]])

    result = np.nonzero(arr)
    row_idx, col_idx = result

    print(f"  Array:\n{arr}")
    print(f"\n  np.nonzero(arr) returns 2 arrays:")
    print(f"    row indices: {row_idx}")  # [0, 1, 1, 2]
    print(f"    col indices: {col_idx}")  # [1, 0, 2, 1]

    # These can be used together to index
    values = arr[row_idx, col_idx]
    print(f"\n  Values at those positions: {values}")  # [1, 2, 3, 4]

    # Or use the tuple directly
    values2 = arr[result]
    print(f"  arr[np.nonzero(arr)] = {values2}")  # [1, 2, 3, 4]

# Demo
print("\n=== 2D Arrays ===")
nonzero_2d()


# =============================================================================
# 4. Getting Coordinates as Pairs
# =============================================================================

def get_coordinates():
    """Convert nonzero output to (row, col) pairs"""
    arr = np.array([[0, 1, 0],
                    [2, 0, 3],
                    [0, 4, 0]])

    row_idx, col_idx = np.nonzero(arr)

    # Method 1: zip
    coords = list(zip(row_idx, col_idx))
    print(f"  Coordinates (zip): {coords}")

    # Method 2: np.argwhere (returns array of coordinates)
    coords2 = np.argwhere(arr != 0)
    print(f"  Coordinates (argwhere):\n{coords2}")

    # Method 3: np.transpose
    coords3 = np.transpose(np.nonzero(arr))
    print(f"  Coordinates (transpose):\n{coords3}")

# Demo
print("\n=== Getting Coordinates ===")
get_coordinates()


# =============================================================================
# 5. Comparison: nonzero vs argwhere vs where
# =============================================================================

def compare_functions():
    """nonzero vs argwhere vs where"""
    arr = np.array([0, 1, 0, 2, 0, 3])

    print(f"  arr = {arr}")

    # np.nonzero: tuple of arrays (one per dimension)
    nz = np.nonzero(arr)
    print(f"\n  np.nonzero(arr) = {nz}")  # (array([1, 3, 5]),)

    # np.argwhere: 2D array of coordinates
    aw = np.argwhere(arr)
    print(f"  np.argwhere(arr) =\n{aw}")  # [[1], [3], [5]]

    # np.where (1-arg): same as nonzero
    w1 = np.where(arr)
    print(f"  np.where(arr) = {w1}")  # (array([1, 3, 5]),)

    # np.where (3-arg): conditional selection
    w3 = np.where(arr > 0, arr, -1)
    print(f"  np.where(arr > 0, arr, -1) = {w3}")  # [-1, 1, -1, 2, -1, 3]

# Demo
print("\n=== nonzero vs argwhere vs where ===")
compare_functions()


# =============================================================================
# 6. Empty Result
# =============================================================================

def nonzero_empty():
    """nonzero on all-zero array returns empty arrays"""
    arr = np.array([0, 0, 0])

    result = np.nonzero(arr)
    print(f"  arr = {arr}")
    print(f"  np.nonzero(arr) = {result}")
    print(f"  result[0].shape = {result[0].shape}")  # (0,)

    # Check if there are any nonzero elements
    if result[0].size == 0:
        print("  No nonzero elements found")

    # Alternative check
    if np.any(arr):
        print("  Has nonzero elements")
    else:
        print("  All zeros (using np.any)")

# Demo
print("\n=== Empty Result ===")
nonzero_empty()


# =============================================================================
# 7. Boolean Arrays
# =============================================================================

def nonzero_boolean():
    """nonzero on boolean arrays finds True positions"""
    arr = np.array([True, False, True, False, True])

    result = np.nonzero(arr)
    print(f"  arr = {arr}")
    print(f"  np.nonzero(arr) = {result}")  # (array([0, 2, 4]),)

    # Same as np.where(arr)
    result2 = np.where(arr)
    print(f"  np.where(arr) = {result2}")  # Same result

    # For boolean, can also use np.flatnonzero
    flat = np.flatnonzero(arr)
    print(f"  np.flatnonzero(arr) = {flat}")  # [0, 2, 4] (just array, not tuple)

# Demo
print("\n=== Boolean Arrays ===")
nonzero_boolean()


# =============================================================================
# 8. flatnonzero
# =============================================================================

def flatnonzero_demo():
    """flatnonzero returns flat indices, not tuple"""
    arr = np.array([[0, 1, 0],
                    [2, 0, 3]])

    # nonzero returns tuple of (row_indices, col_indices)
    nz = np.nonzero(arr)
    print(f"  Array:\n{arr}")
    print(f"  np.nonzero: {nz}")

    # flatnonzero returns flat indices (as if array was flattened)
    flat = np.flatnonzero(arr)
    print(f"  np.flatnonzero: {flat}")  # [1, 3, 5]

    # These are indices into arr.ravel()
    print(f"  arr.ravel() = {arr.ravel()}")  # [0, 1, 0, 2, 0, 3]
    print(f"  arr.ravel()[flat] = {arr.ravel()[flat]}")  # [1, 2, 3]

# Demo
print("\n=== flatnonzero ===")
flatnonzero_demo()


# =============================================================================
# 9. Common Patterns
# =============================================================================

def common_patterns():
    """Common patterns using nonzero"""
    arr = np.array([0, 5, 0, 10, 0, 15, 0])

    print(f"  arr = {arr}")

    # Pattern 1: Get first nonzero index
    indices = np.nonzero(arr)[0]
    if len(indices) > 0:
        first = indices[0]
        print(f"  First nonzero index: {first}")  # 1
        print(f"  First nonzero value: {arr[first]}")  # 5

    # Pattern 2: Get last nonzero index
    if len(indices) > 0:
        last = indices[-1]
        print(f"  Last nonzero index: {last}")  # 5
        print(f"  Last nonzero value: {arr[last]}")  # 15

    # Pattern 3: Count nonzero elements
    count = np.count_nonzero(arr)
    print(f"  Count nonzero: {count}")  # 3

    # Pattern 4: Replace nonzero with specific value
    arr_copy = arr.copy()
    arr_copy[np.nonzero(arr_copy)] = 999
    print(f"  Replace nonzero: {arr_copy}")  # [0, 999, 0, 999, 0, 999, 0]

# Demo
print("\n=== Common Patterns ===")
common_patterns()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.nonzero CHECKLIST:")
print("=" * 60)
print("1. nonzero returns a TUPLE of arrays, one per dimension")
print("2. For 1D array: result[0] gives the indices")
print("3. For 2D array: row_idx, col_idx = result")
print("4. To get VALUES: arr[np.nonzero(arr)] or arr[arr != 0]")
print("5. np.where(arr) with 1 arg is same as nonzero")
print("6. np.argwhere gives coordinates as 2D array of pairs")
print("7. np.flatnonzero gives flat indices (not a tuple)")
print("8. np.count_nonzero counts without finding positions")
print("9. Check result[0].size == 0 for empty result")
