"""
NumPy Broadcasting Errors
=========================
These errors are NOT caught by static analyzers because NumPy doesn't have
static shape analysis. All broadcasting errors occur at runtime.
"""

import numpy as np


# =============================================================================
# Broadcasting Rules Refresher
# =============================================================================
print("=== BROADCASTING RULES ===")
print("1. Shapes align from the RIGHT")
print("2. Dimensions must be EQUAL or ONE (or missing)")
print("3. Size-1 dimensions are 'stretched' to match")
print()
print("Examples:")
print("  (3, 4) + (4,)   -> (3, 4)  # Works: (4,) broadcasts to (3, 4)")
print("  (3, 4) + (3,)   -> ERROR   # Fails: trailing dims 4 != 3")
print("  (3, 4) + (3, 1) -> (3, 4)  # Works: 1 broadcasts to 4")
print("  (3, 1) + (1, 4) -> (3, 4)  # Works: both broadcast")
print()


# =============================================================================
# 1. Shape Mismatch
# =============================================================================

def add_vectors_bad():
    """BAD: Shapes don't broadcast together"""
    arr = np.array([[1, 2, 3, 4],
                    [5, 6, 7, 8],
                    [9, 10, 11, 12]])  # Shape (3, 4)

    vec = np.array([1, 2, 3])  # Shape (3,)

    try:
        result = arr + vec  # ERROR: (3,4) + (3,) - trailing dims don't match!
    except ValueError as e:
        print(f"  ValueError: {e}")
        return None
    return result

def add_vectors_good():
    """GOOD: Reshape vector to broadcast correctly"""
    arr = np.array([[1, 2, 3, 4],
                    [5, 6, 7, 8],
                    [9, 10, 11, 12]])  # Shape (3, 4)

    vec = np.array([1, 2, 3])  # Shape (3,)

    # Option 1: Reshape to column vector (3, 1)
    result = arr + vec.reshape(-1, 1)  # (3, 4) + (3, 1) = (3, 4)

    # Option 2: Use None/np.newaxis
    # result = arr + vec[:, np.newaxis]

    return result

# Demo
print("=== Shape Mismatch ===")
print("arr shape: (3, 4), vec shape: (3,)")
print("BAD (arr + vec):")
add_vectors_bad()
print("GOOD (arr + vec.reshape(-1, 1)):")
print(add_vectors_good())


# =============================================================================
# 2. Unintended Broadcasting
# =============================================================================

def multiply_bad():
    """BAD: Unintended broadcasting creates larger array than expected"""
    a = np.array([[1], [2], [3]])  # Shape (3, 1)
    b = np.array([1, 2, 3, 4])      # Shape (4,)

    # This broadcasts to (3, 4) - might not be intended!
    result = a * b
    print(f"  a shape: {a.shape}, b shape: {b.shape}")
    print(f"  result shape: {result.shape}")  # (3, 4) - surprise!
    return result

def multiply_good():
    """GOOD: Be explicit about shapes and intentions"""
    a = np.array([1, 2, 3])  # Shape (3,)
    b = np.array([1, 2, 3])  # Shape (3,) - same shape

    # Element-wise multiplication - clear intention
    result = a * b
    print(f"  a shape: {a.shape}, b shape: {b.shape}")
    print(f"  result shape: {result.shape}")  # (3,)
    return result

# Demo
print("\n=== Unintended Broadcasting ===")
print("BAD (creates larger array):")
print(multiply_bad())
print("GOOD (explicit shapes):")
print(multiply_good())


# =============================================================================
# 3. Row vs Column Vector Confusion
# =============================================================================

def dot_product_bad():
    """BAD: Confusion between row and column vectors"""
    # 1D arrays don't have row/column concept
    a = np.array([1, 2, 3])  # Shape (3,) - neither row nor column
    b = np.array([4, 5, 6])  # Shape (3,)

    # This works differently than expected if you're thinking matrices
    result1 = a * b      # Element-wise: [4, 10, 18]
    result2 = a @ b      # Dot product: 32

    print(f"  a * b = {result1} (element-wise)")
    print(f"  a @ b = {result2} (dot product)")
    return result1, result2

def matrix_multiply_good():
    """GOOD: Be explicit about dimensions for matrix operations"""
    # If you want matrix multiplication, use 2D arrays
    row = np.array([[1, 2, 3]])     # Shape (1, 3)
    col = np.array([[4], [5], [6]])  # Shape (3, 1)

    result = row @ col  # Shape (1, 1)
    print(f"  row shape: {row.shape}, col shape: {col.shape}")
    print(f"  result: {result} with shape {result.shape}")
    return result

# Demo
print("\n=== Row vs Column Confusion ===")
print("1D array operations:")
dot_product_bad()
print("Explicit 2D matrix operations:")
matrix_multiply_good()


# =============================================================================
# 4. Scalar Broadcast Surprise
# =============================================================================

def scalar_broadcast_demo():
    """Scalar broadcasting always works, but list might not"""
    arr = np.array([1, 2, 3])

    # Scalar broadcast - works fine
    result1 = arr + 1
    print(f"  arr + 1 = {result1}")

    # Single-element list - also works (broadcasts)
    result2 = arr + [1]
    print(f"  arr + [1] = {result2}")

    # Multi-element list - must match shape
    result3 = arr + [1, 1, 1]
    print(f"  arr + [1,1,1] = {result3}")

    # Wrong size list - error!
    try:
        result4 = arr + [1, 1]  # Shape mismatch!
    except ValueError as e:
        print(f"  arr + [1,1] raises: {e}")

# Demo
print("\n=== Scalar and List Broadcasting ===")
scalar_broadcast_demo()


# =============================================================================
# 5. Broadcasting with Boolean Masks
# =============================================================================

def mask_bad():
    """BAD: Mask shape doesn't match array shape"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])  # Shape (2, 3)

    mask = np.array([True, False])  # Shape (2,) - wrong!

    try:
        result = arr[mask]  # This actually works but might not do what you expect
        print(f"  arr[mask] = {result}")  # Selects rows!
    except Exception as e:
        print(f"  Error: {e}")

def mask_good():
    """GOOD: Mask shape matches array shape"""
    arr = np.array([[1, 2, 3],
                    [4, 5, 6]])  # Shape (2, 3)

    # Element-wise mask
    mask = arr > 3
    print(f"  mask (arr > 3):\n{mask}")
    result = arr[mask]
    print(f"  arr[mask] = {result}")  # [4, 5, 6]

# Demo
print("\n=== Boolean Mask Broadcasting ===")
print("BAD (wrong mask shape):")
mask_bad()
print("GOOD (element-wise mask):")
mask_good()


# =============================================================================
# 6. Assignment Broadcasting
# =============================================================================

def assignment_bad():
    """BAD: Broadcast assignment can be confusing"""
    arr = np.zeros((3, 4))

    # This sets ALL elements to 1 (scalar broadcast)
    arr[:] = 1
    print(f"  arr[:] = 1:\n{arr}")

    # This sets each ROW (broadcasts along columns)
    arr[:] = np.array([1, 2, 3, 4])
    print(f"  arr[:] = [1,2,3,4]:\n{arr}")

def assignment_good():
    """GOOD: Be explicit about what you're assigning"""
    arr = np.zeros((3, 4))

    # Explicit column assignment
    arr[:, 0] = [1, 2, 3]  # First column
    print(f"  Set first column:\n{arr}")

    # Explicit row assignment
    arr[0, :] = [10, 20, 30, 40]  # First row
    print(f"  Set first row:\n{arr}")

# Demo
print("\n=== Assignment Broadcasting ===")
print("Broadcasting assignments:")
assignment_bad()
print("Explicit assignments:")
assignment_good()


# =============================================================================
# 7. Outer Product vs Element-wise
# =============================================================================

def outer_vs_elementwise():
    """Common confusion between outer product and element-wise"""
    a = np.array([1, 2, 3])
    b = np.array([10, 20, 30])

    # Element-wise (same shape)
    elementwise = a * b
    print(f"  Element-wise (a * b): {elementwise}")  # [10, 40, 90]

    # Outer product (broadcasting)
    outer = a.reshape(-1, 1) * b.reshape(1, -1)
    print(f"  Outer product:\n{outer}")

    # Or use np.outer()
    outer2 = np.outer(a, b)
    print(f"  np.outer(a, b):\n{outer2}")

# Demo
print("\n=== Outer Product vs Element-wise ===")
outer_vs_elementwise()


# =============================================================================
# 8. Debugging Broadcasting Issues
# =============================================================================

def debug_broadcasting(a, b, operation='+'):
    """Helper function to debug broadcasting"""
    print(f"  a.shape = {a.shape}")
    print(f"  b.shape = {b.shape}")

    # Check if shapes are compatible
    a_shape = list(a.shape)
    b_shape = list(b.shape)

    # Pad shorter shape with 1s on the left
    max_len = max(len(a_shape), len(b_shape))
    a_shape = [1] * (max_len - len(a_shape)) + a_shape
    b_shape = [1] * (max_len - len(b_shape)) + b_shape

    result_shape = []
    compatible = True
    for i, (x, y) in enumerate(zip(a_shape, b_shape)):
        if x == y:
            result_shape.append(x)
        elif x == 1:
            result_shape.append(y)
        elif y == 1:
            result_shape.append(x)
        else:
            compatible = False
            print(f"  INCOMPATIBLE at dimension {i}: {x} vs {y}")

    if compatible:
        print(f"  Result shape would be: {tuple(result_shape)}")

    return compatible

# Demo
print("\n=== Debugging Broadcasting ===")
print("Check (3, 4) + (4,):")
debug_broadcasting(np.zeros((3, 4)), np.zeros(4))
print("\nCheck (3, 4) + (3,):")
debug_broadcasting(np.zeros((3, 4)), np.zeros(3))
print("\nCheck (3, 1, 4) + (2, 1):")
debug_broadcasting(np.zeros((3, 1, 4)), np.zeros((2, 1)))


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("BROADCASTING CHECKLIST:")
print("=" * 60)
print("1. Shapes align from the RIGHT")
print("2. Dimensions must be equal or 1")
print("3. Print shapes before operations: print(arr.shape)")
print("4. Use reshape() or np.newaxis to fix dimensions")
print("5. Be explicit: (n,) is different from (n, 1) and (1, n)")
print("6. For row vectors: arr.reshape(1, -1)")
print("7. For column vectors: arr.reshape(-1, 1)")
print("8. Use np.outer() for outer products")
print("9. Boolean masks should match array shape")
