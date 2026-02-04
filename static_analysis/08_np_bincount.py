"""
np.bincount Requirements
========================
These errors are NOT caught by static analyzers because they involve
runtime value constraints (non-negative integers).
"""

import numpy as np


# =============================================================================
# 1. Negative Values
# =============================================================================

def bincount_negative_bad():
    """BAD: bincount doesn't accept negative values"""
    arr = np.array([-1, 0, 1, 2, 1, 0])

    try:
        result = np.bincount(arr)  # ValueError!
    except ValueError as e:
        print(f"  ValueError: {e}")

def bincount_negative_good():
    """GOOD: Filter negatives or shift values"""
    arr = np.array([-1, 0, 1, 2, 1, 0])

    # Option 1: Filter out negatives
    positive_only = arr[arr >= 0]
    result1 = np.bincount(positive_only)
    print(f"  Filter negatives: {result1}")  # [2, 2, 1]

    # Option 2: Shift values to make all non-negative
    min_val = arr.min()
    shifted = arr - min_val  # Now all >= 0
    result2 = np.bincount(shifted)
    print(f"  Shift values: {result2}")  # [1, 2, 2, 1]
    print(f"  (indices now represent {min_val} to {arr.max()})")

# Demo
print("=== Negative Values ===")
print("arr = [-1, 0, 1, 2, 1, 0]")
print("\nBAD:")
bincount_negative_bad()
print("\nGOOD:")
bincount_negative_good()


# =============================================================================
# 2. Non-integer Input
# =============================================================================

def bincount_float_bad():
    """BAD: bincount requires integers"""
    arr = np.array([1.5, 2.5, 1.5, 3.5])

    try:
        result = np.bincount(arr)  # TypeError!
    except TypeError as e:
        print(f"  TypeError: {e}")

def bincount_float_good():
    """GOOD: Convert to int first (with explicit rounding choice)"""
    arr = np.array([1.5, 2.5, 1.5, 3.5])

    # Option 1: Floor (truncate)
    as_int = arr.astype(int)
    result1 = np.bincount(as_int)
    print(f"  Floor to int: {as_int} -> bincount: {result1}")

    # Option 2: Round
    rounded = np.round(arr).astype(int)
    result2 = np.bincount(rounded)
    print(f"  Rounded: {rounded} -> bincount: {result2}")

# Demo
print("\n=== Non-integer Input ===")
print("arr = [1.5, 2.5, 1.5, 3.5]")
print("\nBAD:")
bincount_float_bad()
print("\nGOOD:")
bincount_float_good()


# =============================================================================
# 3. Weights Shape Mismatch
# =============================================================================

def bincount_weights_bad():
    """BAD: weights must have same length as input"""
    arr = np.array([0, 1, 1, 2])
    weights = np.array([1.0, 2.0, 3.0])  # Wrong length!

    try:
        result = np.bincount(arr, weights=weights)  # ValueError!
    except ValueError as e:
        print(f"  ValueError: {e}")

def bincount_weights_good():
    """GOOD: weights must match input length"""
    arr = np.array([0, 1, 1, 2])
    weights = np.array([1.0, 2.0, 3.0, 4.0])  # Same length

    result = np.bincount(arr, weights=weights)
    print(f"  arr = {arr}")
    print(f"  weights = {weights}")
    print(f"  bincount(arr, weights) = {result}")
    # Result: [1.0, 5.0, 4.0]
    # index 0: weight 1.0 (arr[0]=0)
    # index 1: weights 2.0+3.0=5.0 (arr[1]=1, arr[2]=1)
    # index 2: weight 4.0 (arr[3]=2)

# Demo
print("\n=== Weights Shape Mismatch ===")
print("arr = [0, 1, 1, 2]")
print("\nBAD (wrong weights length):")
bincount_weights_bad()
print("\nGOOD (correct weights length):")
bincount_weights_good()


# =============================================================================
# 4. minlength Misunderstanding
# =============================================================================

def minlength_demo():
    """Output length is max(max(x)+1, minlength)"""
    arr = np.array([0, 1, 1, 2])

    # Without minlength: length is max(arr) + 1
    result1 = np.bincount(arr)
    print(f"  bincount([0,1,1,2]) = {result1}")  # [1, 2, 1]
    print(f"  Length: {len(result1)}")  # 3

    # With minlength smaller than needed: ignored
    result2 = np.bincount(arr, minlength=2)
    print(f"\n  bincount(..., minlength=2) = {result2}")  # Still [1, 2, 1]
    print(f"  Length: {len(result2)}")  # 3 (minlength=2 is too small)

    # With minlength larger: pads with zeros
    result3 = np.bincount(arr, minlength=6)
    print(f"\n  bincount(..., minlength=6) = {result3}")  # [1, 2, 1, 0, 0, 0]
    print(f"  Length: {len(result3)}")  # 6

# Demo
print("\n=== minlength Behavior ===")
minlength_demo()


# =============================================================================
# 5. Empty Array
# =============================================================================

def bincount_empty():
    """bincount on empty array returns empty array"""
    empty = np.array([], dtype=int)

    result = np.bincount(empty)
    print(f"  bincount([]) = {result}")  # []
    print(f"  Shape: {result.shape}")    # (0,)

    # With minlength: returns zeros
    result2 = np.bincount(empty, minlength=5)
    print(f"  bincount([], minlength=5) = {result2}")  # [0, 0, 0, 0, 0]

# Demo
print("\n=== Empty Array ===")
bincount_empty()


# =============================================================================
# 6. Common Use Cases
# =============================================================================

def histogram_with_bincount():
    """bincount is fast for integer histograms"""
    # Count occurrences of each value
    data = np.array([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])

    counts = np.bincount(data)
    print(f"  data = {data}")
    print(f"  bincount = {counts}")
    print(f"  Meaning: 0 appears {counts[0]} times, 1 appears {counts[1]} times, etc.")

    # Find mode (most common value)
    mode = np.argmax(counts)
    print(f"\n  Mode (most common): {mode} (appears {counts[mode]} times)")

def weighted_average_per_group():
    """Use bincount to compute group-wise weighted sums"""
    groups = np.array([0, 0, 1, 1, 1, 2])  # Group labels
    values = np.array([1, 2, 3, 4, 5, 6])  # Values to sum
    weights = np.array([1, 1, 1, 1, 1, 1])  # Optional weights

    # Sum values per group
    group_sums = np.bincount(groups, weights=values.astype(float))
    group_counts = np.bincount(groups)
    group_means = group_sums / group_counts

    print(f"  groups = {groups}")
    print(f"  values = {values}")
    print(f"  Group sums: {group_sums}")      # [3, 12, 6]
    print(f"  Group counts: {group_counts}")  # [2, 3, 1]
    print(f"  Group means: {group_means}")    # [1.5, 4, 6]

# Demo
print("\n=== Use Case: Histogram ===")
histogram_with_bincount()
print("\n=== Use Case: Group Statistics ===")
weighted_average_per_group()


# =============================================================================
# 7. Comparison with np.unique
# =============================================================================

def bincount_vs_unique():
    """bincount vs unique for counting"""
    arr = np.array([3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5])

    # bincount: returns counts for ALL indices 0 to max(arr)
    bc = np.bincount(arr)
    print(f"  bincount: {bc}")  # [0, 2, 1, 2, 1, 3, 1, 0, 0, 1]

    # unique: returns only values that exist
    values, counts = np.unique(arr, return_counts=True)
    print(f"  unique values: {values}")  # [1, 2, 3, 4, 5, 6, 9]
    print(f"  unique counts: {counts}")  # [2, 1, 2, 1, 3, 1, 1]

    # bincount is faster when values are dense integers
    # unique is better for sparse or non-integer data

# Demo
print("\n=== bincount vs unique ===")
bincount_vs_unique()


# =============================================================================
# 8. Large Values
# =============================================================================

def bincount_large():
    """Large values create large output arrays"""
    arr = np.array([0, 1000000])  # Small array, but...

    result = np.bincount(arr)
    print(f"  arr = {arr}")
    print(f"  bincount length: {len(result)}")  # 1000001!
    print(f"  Memory: ~{result.nbytes / 1024:.1f} KB")

    # This can cause memory issues with very large values
    # Consider using unique + value_counts for sparse data

# Demo
print("\n=== Large Values ===")
bincount_large()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.bincount CHECKLIST:")
print("=" * 60)
print("1. Input must be non-negative integers")
print("2. Filter negatives: arr[arr >= 0]")
print("3. Or shift: arr - arr.min() to make non-negative")
print("4. weights must have same length as input array")
print("5. Output length is max(max(x)+1, minlength)")
print("6. minlength only EXTENDS, never shrinks output")
print("7. Empty array returns empty (or zeros with minlength)")
print("8. Large values create large arrays - check memory!")
print("9. Use unique() for sparse or non-integer data")
