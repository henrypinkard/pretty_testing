"""
Recursion Errors and Fixes
==========================
These errors are NOT caught by static analyzers because they involve control flow
and logic that cannot be determined statically.
"""

import sys

# Set a lower recursion limit for demo purposes (to fail faster)
# Default is usually 1000
# sys.setrecursionlimit(100)


# =============================================================================
# 1. Wrong Base Case
# =============================================================================

def factorial_bad(n):
    """BAD: Base case only handles n == 0, not negative numbers"""
    if n == 0:
        return 1
    return n * factorial_bad(n - 1)

def factorial_good(n):
    """GOOD: Handle edge cases properly"""
    if n <= 0:  # Handle 0 AND negative numbers
        return 1
    return n * factorial_good(n - 1)

# Demo
print("=== Wrong Base Case ===")
print(f"factorial_good(5) = {factorial_good(5)}")  # 120
print(f"factorial_good(0) = {factorial_good(0)}")  # 1
print(f"factorial_good(-1) = {factorial_good(-1)}")  # 1 (handled!)

# This would cause RecursionError:
# print(f"factorial_bad(-1) = {factorial_bad(-1)}")  # Infinite recursion!


# =============================================================================
# 2. Missing Base Case
# =============================================================================

def countdown_bad(n):
    """BAD: No base case at all!"""
    print(n)
    countdown_bad(n - 1)  # Never stops!

def countdown_good(n):
    """GOOD: Has proper base case"""
    if n <= 0:
        print("Done!")
        return
    print(n)
    countdown_good(n - 1)

# Demo
print("\n=== Missing Base Case ===")
print("Good countdown:")
countdown_good(3)

# This would cause RecursionError:
# countdown_bad(3)


# =============================================================================
# 3. Wrong Recursive Step
# =============================================================================

def sum_to_n_bad(n):
    """BAD: Recursive call doesn't change the argument!"""
    if n <= 0:
        return 0
    return n + sum_to_n_bad(n)  # Should be n - 1!

def sum_to_n_good(n):
    """GOOD: Proper recursive step"""
    if n <= 0:
        return 0
    return n + sum_to_n_good(n - 1)

# Demo
print("\n=== Wrong Recursive Step ===")
print(f"sum_to_n_good(5) = {sum_to_n_good(5)}")  # 15 (5+4+3+2+1)

# This would cause RecursionError:
# print(f"sum_to_n_bad(5) = {sum_to_n_bad(5)}")


# =============================================================================
# 4. Not Returning Recursive Call
# =============================================================================

def find_max_bad(lst, idx=0, current_max=None):
    """BAD: Forgot to return the recursive call!"""
    if idx >= len(lst):
        return current_max
    if current_max is None or lst[idx] > current_max:
        current_max = lst[idx]
    find_max_bad(lst, idx + 1, current_max)  # Missing return!

def find_max_good(lst, idx=0, current_max=None):
    """GOOD: Return the recursive call"""
    if idx >= len(lst):
        return current_max
    if current_max is None or lst[idx] > current_max:
        current_max = lst[idx]
    return find_max_good(lst, idx + 1, current_max)

# Demo
print("\n=== Not Returning Recursive Call ===")
lst = [3, 1, 4, 1, 5, 9, 2, 6]
print(f"List: {lst}")
print(f"find_max_bad: {find_max_bad(lst)}")   # None! (forgot return)
print(f"find_max_good: {find_max_good(lst)}")  # 9


# =============================================================================
# 5. Off-by-One in Recursion
# =============================================================================

def sum_list_bad(lst, idx=0):
    """BAD: Off-by-one - starts at wrong index or misses element"""
    if idx >= len(lst):
        return 0
    return lst[idx] + sum_list_bad(lst, idx + 2)  # Skipping elements!

def sum_list_good(lst, idx=0):
    """GOOD: Process every element"""
    if idx >= len(lst):
        return 0
    return lst[idx] + sum_list_good(lst, idx + 1)

# Demo
print("\n=== Off-by-One ===")
lst = [1, 2, 3, 4, 5]
print(f"List: {lst}")
print(f"sum_list_bad (skips): {sum_list_bad(lst)}")   # 9 (1+3+5, skipped 2,4)
print(f"sum_list_good: {sum_list_good(lst)}")          # 15 (1+2+3+4+5)


# =============================================================================
# 6. Accumulator Not Passed Correctly
# =============================================================================

def reverse_string_bad(s, result=""):
    """BAD: Not using the accumulator in recursive call"""
    if not s:
        return result
    result = s[-1] + result  # Local modification only!
    return reverse_string_bad(s[:-1])  # Forgot to pass result!

def reverse_string_good(s, result=""):
    """GOOD: Pass accumulator correctly"""
    if not s:
        return result
    return reverse_string_good(s[:-1], result + s[-1])

# Demo
print("\n=== Accumulator Not Passed ===")
s = "hello"
print(f"String: {s}")
print(f"reverse_string_bad: '{reverse_string_bad(s)}'")   # '' (empty!)
print(f"reverse_string_good: '{reverse_string_good(s)}'")  # 'olleh'


# =============================================================================
# 7. Mutual Recursion Gone Wrong
# =============================================================================

def is_even_bad(n):
    """BAD: Doesn't handle negative numbers"""
    if n == 0:
        return True
    return is_odd_bad(n - 1)

def is_odd_bad(n):
    """BAD: Doesn't handle negative numbers"""
    if n == 0:
        return False
    return is_even_bad(n - 1)

def is_even_good(n):
    """GOOD: Handle negative numbers"""
    n = abs(n)
    if n == 0:
        return True
    return is_odd_good(n - 1)

def is_odd_good(n):
    """GOOD: Handle negative numbers"""
    n = abs(n)
    if n == 0:
        return False
    return is_even_good(n - 1)

# Demo
print("\n=== Mutual Recursion ===")
print(f"is_even_good(4) = {is_even_good(4)}")   # True
print(f"is_even_good(-4) = {is_even_good(-4)}")  # True
print(f"is_odd_good(3) = {is_odd_good(3)}")     # True

# This would cause RecursionError:
# print(f"is_even_bad(-4) = {is_even_bad(-4)}")


# =============================================================================
# 8. Tree Recursion - Processing Order Matters
# =============================================================================

def tree_sum_bad(node):
    """BAD: Wrong order can miss nodes or double-count"""
    if node is None:
        return 0
    # If this were a tree traversal doing side effects, order matters!
    return node['value'] + tree_sum_bad(node.get('left')) + tree_sum_bad(node.get('left'))  # Oops! 'left' twice!

def tree_sum_good(node):
    """GOOD: Process both children"""
    if node is None:
        return 0
    return node['value'] + tree_sum_good(node.get('left')) + tree_sum_good(node.get('right'))

# Demo
print("\n=== Tree Recursion ===")
tree = {
    'value': 1,
    'left': {'value': 2, 'left': None, 'right': None},
    'right': {'value': 3, 'left': None, 'right': None}
}
print(f"Tree: root=1, left=2, right=3")
print(f"tree_sum_bad (left twice): {tree_sum_bad(tree)}")   # 5 (1+2+2, missed right!)
print(f"tree_sum_good: {tree_sum_good(tree)}")              # 6 (1+2+3)


# =============================================================================
# Debugging Helper
# =============================================================================

def factorial_debug(n, depth=0):
    """Helper: Add tracing to debug recursion"""
    indent = "  " * depth
    print(f"{indent}factorial_debug({n})")

    if n <= 0:
        print(f"{indent}  -> base case, returning 1")
        return 1

    result = n * factorial_debug(n - 1, depth + 1)
    print(f"{indent}  -> returning {n} * ... = {result}")
    return result

print("\n=== Debugging Recursion ===")
print("Tracing factorial_debug(4):")
result = factorial_debug(4)
print(f"Final result: {result}")


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("RECURSION DEBUGGING CHECKLIST:")
print("=" * 60)
print("1. Base case: Does it handle ALL termination conditions?")
print("2. Base case: Does it handle edge cases (0, negative, empty)?")
print("3. Recursive step: Does argument CHANGE toward base case?")
print("4. Return: Is the recursive call's result returned?")
print("5. Accumulator: Is it passed correctly to recursive call?")
print("6. Off-by-one: Are you processing the right elements?")
print("7. Add print statements to trace execution!")
