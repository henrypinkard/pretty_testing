"""
List Comprehension Pitfalls
===========================
These errors are NOT caught by static analyzers because they are logic errors.
"""

# =============================================================================
# 1. Wrong Filter Logic
# =============================================================================

def filter_positive_bad(items):
    """BAD: Using > when >= was intended"""
    return [x for x in items if x > 0]  # Excludes 0!

def filter_positive_good(items):
    """GOOD: Include zero if that's what you need"""
    return [x for x in items if x >= 0]  # Includes 0

# Demo
print("=== Filter Logic ===")
items = [-1, 0, 1, 2]
print(f"Items: {items}")
print(f"BAD (x > 0):  {filter_positive_bad(items)}")   # [1, 2] - missing 0!
print(f"GOOD (x >= 0): {filter_positive_good(items)}")  # [0, 1, 2]


# =============================================================================
# 2. Wrong Transformation
# =============================================================================

def double_values_bad(items):
    """BAD: Multiplying when squaring was intended"""
    return [x * 2 for x in items]  # x * 2 != x ** 2

def square_values_good(items):
    """GOOD: Square the values"""
    return [x ** 2 for x in items]

# Demo
print("\n=== Transformation ===")
items = [1, 2, 3, 4]
print(f"Items: {items}")
print(f"BAD (x * 2):  {double_values_bad(items)}")   # [2, 4, 6, 8]
print(f"GOOD (x ** 2): {square_values_good(items)}")  # [1, 4, 9, 16]


# =============================================================================
# 3. Variable Shadowing in Nested Comprehensions
# =============================================================================

def flatten_matrix_bad(matrix):
    """BAD: Inner x shadows outer x - confusing and error-prone"""
    return [[x for x in row] for x in matrix]  # Both use 'x'!

def flatten_matrix_good(matrix):
    """GOOD: Use distinct variable names"""
    return [[cell for cell in row] for row in matrix]

# Demo
print("\n=== Variable Shadowing ===")
matrix = [[1, 2], [3, 4], [5, 6]]
print(f"Matrix: {matrix}")
print(f"BAD (shadowed x):  {flatten_matrix_bad(matrix)}")
print(f"GOOD (distinct names): {flatten_matrix_good(matrix)}")
# Both produce same output here, but the BAD version is confusing
# The real danger: outer 'x' is not accessible in outer scope after comprehension


# More dangerous shadowing example
print("\n=== Dangerous Shadowing Example ===")
x = 100  # Outer variable
result_bad = [x for x in [1, 2, 3]]  # Shadows outer x
print(f"After comprehension, x = {x}")  # In Python 3, x is still 100 (fixed from Python 2)
# But inside nested comprehensions, shadowing causes real confusion:

def process_with_outer_bad():
    """BAD: Trying to use outer variable but it's shadowed"""
    multiplier = 10
    matrix = [[1, 2], [3, 4]]
    # Confusing: which 'x' is which?
    return [[x * multiplier for x in row] for x in matrix]

def process_with_outer_good():
    """GOOD: Clear variable names"""
    multiplier = 10
    matrix = [[1, 2], [3, 4]]
    return [[cell * multiplier for cell in row] for row in matrix]


# =============================================================================
# 4. Empty Result Unexpectedly
# =============================================================================

def filter_large_bad(items, threshold=1000):
    """BAD: Filter may remove everything"""
    return [x for x in items if x > threshold]

def filter_large_good(items, threshold=1000):
    """GOOD: Handle empty case or validate"""
    result = [x for x in items if x > threshold]
    if not result:
        print(f"Warning: No items found above threshold {threshold}")
    return result

# Demo
print("\n=== Empty Result ===")
items = [1, 2, 3, 4, 5]
print(f"Items: {items}")
print(f"BAD (threshold=1000): {filter_large_bad(items)}")  # [] - silent empty!
print(f"GOOD (threshold=1000): {filter_large_good(items)}")  # [] with warning


# =============================================================================
# 5. Modifying While Iterating (via comprehension)
# =============================================================================

def remove_evens_bad(items):
    """BAD: Creating a list that looks like it modifies the original"""
    # This creates a NEW list, doesn't modify items
    filtered = [x for x in items if x % 2 != 0]
    # Common mistake: forgetting to use 'filtered'
    return items  # Returns original!

def remove_evens_good(items):
    """GOOD: Return the filtered list"""
    return [x for x in items if x % 2 != 0]

# Demo
print("\n=== Return Value Mistake ===")
items = [1, 2, 3, 4, 5]
print(f"Items: {items}")
print(f"BAD (returns original): {remove_evens_bad(items)}")   # [1, 2, 3, 4, 5]
print(f"GOOD (returns filtered): {remove_evens_good(items)}")  # [1, 3, 5]


# =============================================================================
# 6. Side Effects in Comprehensions
# =============================================================================

counter = 0

def count_and_transform_bad(items):
    """BAD: Side effects in comprehension - hard to debug"""
    global counter
    return [((counter := counter + 1), x * 2)[1] for x in items]  # Walrus abuse

def count_and_transform_good(items):
    """GOOD: Keep side effects separate"""
    count = len(items)
    transformed = [x * 2 for x in items]
    return transformed, count

# Demo
print("\n=== Side Effects ===")
items = [1, 2, 3]
counter = 0
result_bad = count_and_transform_bad(items)
print(f"BAD: result={result_bad}, counter={counter}")

result_good, count = count_and_transform_good(items)
print(f"GOOD: result={result_good}, count={count}")


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("CHECKLIST FOR LIST COMPREHENSIONS:")
print("=" * 60)
print("1. Check filter conditions: > vs >= vs == vs !=")
print("2. Verify transformation: * vs ** vs + vs //")
print("3. Use distinct variable names in nested comprehensions")
print("4. Handle empty results explicitly")
print("5. Don't forget to use/return the comprehension result")
print("6. Avoid side effects in comprehensions")
