"""
np.random.RandomState Usage
===========================
These errors are NOT caught by static analyzers because method names are valid
and parameter order is a logic error, not a syntax error.
"""

import numpy as np


# =============================================================================
# 1. Forgetting Seed (Reproducibility)
# =============================================================================

def random_bad():
    """BAD: Results not reproducible"""
    result1 = np.random.random(5)
    result2 = np.random.random(5)
    print(f"  First call: {result1}")
    print(f"  Second call: {result2}")
    print(f"  Same? {np.allclose(result1, result2)}")  # False (almost certainly)

def random_good():
    """GOOD: Set seed for reproducibility"""
    np.random.seed(42)
    result1 = np.random.random(5)

    np.random.seed(42)  # Reset seed
    result2 = np.random.random(5)

    print(f"  First call: {result1}")
    print(f"  Second call: {result2}")
    print(f"  Same? {np.allclose(result1, result2)}")  # True!

def random_best():
    """BEST: Use explicit RandomState/Generator"""
    rng = np.random.RandomState(42)
    result1 = rng.random(5)

    rng2 = np.random.RandomState(42)
    result2 = rng2.random(5)

    print(f"  RandomState 1: {result1}")
    print(f"  RandomState 2: {result2}")
    print(f"  Same? {np.allclose(result1, result2)}")  # True!

# Demo
print("=== Reproducibility ===")
print("BAD (no seed):")
random_bad()
print("\nGOOD (global seed):")
random_good()
print("\nBEST (explicit RandomState):")
random_best()


# =============================================================================
# 2. Method Name Confusion
# =============================================================================

def method_confusion():
    """Different methods with similar names"""
    rng = np.random.RandomState(42)

    print("  Different methods for random floats in [0, 1):")

    # These all do the same thing!
    r1 = rng.random(3)          # NumPy 1.17+ preferred
    print(f"    rng.random(3): {r1}")

    rng = np.random.RandomState(42)  # Reset
    r2 = rng.random_sample(3)   # Old name
    print(f"    rng.random_sample(3): {r2}")

    rng = np.random.RandomState(42)  # Reset
    r3 = rng.rand(3)            # MATLAB-like
    print(f"    rng.rand(3): {r3}")

    # All produce same values with same seed
    print(f"    All same? {np.allclose(r1, r2) and np.allclose(r2, r3)}")

# Demo
print("\n=== Method Name Confusion ===")
method_confusion()


# =============================================================================
# 3. Shape: Tuple vs Arguments
# =============================================================================

def shape_confusion():
    """Different methods take shape differently!"""
    rng = np.random.RandomState(42)

    # rand() takes separate dimensions (MATLAB-style)
    r1 = rng.rand(3, 4)
    print(f"  rng.rand(3, 4) shape: {r1.shape}")

    # random() takes a tuple (or single int)
    r2 = rng.random((3, 4))
    print(f"  rng.random((3, 4)) shape: {r2.shape}")

    # Common mistake with random():
    r3 = rng.random(3)  # This gives shape (3,), not error
    print(f"  rng.random(3) shape: {r3.shape}")

    # randn() also takes separate dimensions
    r4 = rng.randn(3, 4)
    print(f"  rng.randn(3, 4) shape: {r4.shape}")

    # standard_normal() takes tuple
    r5 = rng.standard_normal((3, 4))
    print(f"  rng.standard_normal((3, 4)) shape: {r5.shape}")

# Demo
print("\n=== Shape: Tuple vs Arguments ===")
shape_confusion()


# =============================================================================
# 4. Distribution Parameter Order
# =============================================================================

def param_order_bad():
    """BAD: Wrong parameter order for normal()"""
    rng = np.random.RandomState(42)

    # WRONG: normal(std, mean) - order is swapped!
    mean = 100
    std = 5
    samples = rng.normal(std, mean, size=1000)  # WRONG!
    print(f"  Intended: mean=100, std=5")
    print(f"  BAD result mean: {samples.mean():.1f}")  # ~5 (wrong!)
    print(f"  BAD result std: {samples.std():.1f}")   # ~100 (wrong!)

def param_order_good():
    """GOOD: Correct parameter order (loc, scale)"""
    rng = np.random.RandomState(42)

    # CORRECT: normal(mean, std) or normal(loc=, scale=)
    mean = 100
    std = 5
    samples = rng.normal(mean, std, size=1000)  # loc, scale
    print(f"  Intended: mean=100, std=5")
    print(f"  GOOD result mean: {samples.mean():.1f}")  # ~100
    print(f"  GOOD result std: {samples.std():.1f}")   # ~5

    # Best: use keyword arguments to be explicit
    samples2 = rng.normal(loc=mean, scale=std, size=1000)
    print(f"  With keywords: mean={samples2.mean():.1f}, std={samples2.std():.1f}")

# Demo
print("\n=== Distribution Parameter Order ===")
print("BAD (swapped mean/std):")
param_order_bad()
print("\nGOOD (correct order):")
param_order_good()


# =============================================================================
# 5. Integer Range (randint)
# =============================================================================

def randint_demo():
    """randint: high is EXCLUSIVE"""
    rng = np.random.RandomState(42)

    # randint(low, high) - high is EXCLUSIVE
    samples = rng.randint(0, 10, size=20)
    print(f"  randint(0, 10): {samples}")
    print(f"  Max value: {samples.max()}")  # 9, not 10!
    print(f"  Contains 10? {10 in samples}")  # False

    # If you want to include high:
    samples2 = rng.randint(0, 11, size=20)  # Use high+1
    print(f"\n  randint(0, 11) for [0,10]: {samples2}")

    # Or use random.choice (deprecated style)
    samples3 = rng.choice(11, size=20)  # [0, 10] inclusive
    print(f"  choice(11): {samples3}")

# Demo
print("\n=== randint Range ===")
randint_demo()


# =============================================================================
# 6. State Mutation
# =============================================================================

def state_mutation():
    """RandomState is stateful - each call changes state"""
    rng = np.random.RandomState(42)

    # Each call advances the state
    r1 = rng.random()
    r2 = rng.random()
    r3 = rng.random()
    print(f"  Three calls: {r1:.4f}, {r2:.4f}, {r3:.4f}")
    print(f"  All different!")

    # Reusing same rng gives different results
    def bad_function(rng):
        """BAD: Function changes external state"""
        return rng.random(3)

    rng = np.random.RandomState(42)
    result1 = bad_function(rng)
    result2 = bad_function(rng)  # Different! State was mutated
    print(f"\n  First call: {result1}")
    print(f"  Second call: {result2}")
    print(f"  Same? {np.allclose(result1, result2)}")  # False!

    # GOOD: Create fresh rng each time for reproducibility
    result3 = np.random.RandomState(42).random(3)
    result4 = np.random.RandomState(42).random(3)
    print(f"\n  Fresh RNG 1: {result3}")
    print(f"  Fresh RNG 2: {result4}")
    print(f"  Same? {np.allclose(result3, result4)}")  # True!

# Demo
print("\n=== State Mutation ===")
state_mutation()


# =============================================================================
# 7. RandomState vs Generator (NumPy 1.17+)
# =============================================================================

def new_generator():
    """Modern NumPy uses Generator, not RandomState"""
    # Old way (still works)
    rng_old = np.random.RandomState(42)

    # New way (NumPy 1.17+) - preferred
    rng_new = np.random.default_rng(42)

    print("  Old RandomState methods:")
    print(f"    rng.rand(3): {rng_old.rand(3)}")
    print(f"    rng.randn(3): {rng_old.randn(3)}")

    print("\n  New Generator methods:")
    print(f"    rng.random(3): {rng_new.random(3)}")
    print(f"    rng.standard_normal(3): {rng_new.standard_normal(3)}")

    # Key differences:
    # - Generator has different random algorithm (PCG64 vs Mersenne Twister)
    # - Generator has no rand/randn (use random/standard_normal)
    # - Generator has no randint (use integers)

# Demo
print("\n=== RandomState vs Generator ===")
new_generator()


# =============================================================================
# 8. Shuffling and Permutation
# =============================================================================

def shuffle_demo():
    """shuffle vs permutation"""
    rng = np.random.RandomState(42)

    arr = np.array([1, 2, 3, 4, 5])

    # shuffle modifies IN PLACE and returns None!
    arr_copy = arr.copy()
    result = rng.shuffle(arr_copy)
    print(f"  Original: {arr}")
    print(f"  After shuffle: {arr_copy}")
    print(f"  shuffle() returns: {result}")  # None!

    # permutation returns a NEW array
    rng = np.random.RandomState(42)
    result2 = rng.permutation(arr)
    print(f"\n  permutation() returns: {result2}")
    print(f"  Original unchanged: {arr}")

# Demo
print("\n=== Shuffle vs Permutation ===")
shuffle_demo()


# =============================================================================
# 9. Choice with/without Replacement
# =============================================================================

def choice_demo():
    """choice default is WITH replacement"""
    rng = np.random.RandomState(42)

    arr = np.array([10, 20, 30, 40, 50])

    # Default: with replacement (can pick same element multiple times)
    samples1 = rng.choice(arr, size=10, replace=True)
    print(f"  arr = {arr}")
    print(f"  choice(arr, 10, replace=True): {samples1}")

    # Without replacement: each element at most once
    samples2 = rng.choice(arr, size=5, replace=False)
    print(f"  choice(arr, 5, replace=False): {samples2}")

    # Error if size > len(arr) without replacement
    try:
        samples3 = rng.choice(arr, size=10, replace=False)
    except ValueError as e:
        print(f"  choice(arr, 10, replace=False) raises: {e}")

# Demo
print("\n=== Choice Replacement ===")
choice_demo()


# =============================================================================
# 10. Common Distributions
# =============================================================================

def distributions_demo():
    """Quick reference for common distributions"""
    rng = np.random.RandomState(42)

    print("  Uniform [0, 1):")
    print(f"    rng.random(3): {rng.random(3)}")

    print("\n  Uniform [low, high):")
    print(f"    rng.uniform(0, 10, 3): {rng.uniform(0, 10, 3)}")

    print("\n  Normal (Gaussian):")
    print(f"    rng.normal(loc=0, scale=1, size=3): {rng.normal(0, 1, 3)}")

    print("\n  Integers [low, high):")
    print(f"    rng.randint(0, 100, 3): {rng.randint(0, 100, 3)}")

    print("\n  Binomial:")
    print(f"    rng.binomial(n=10, p=0.5, size=3): {rng.binomial(10, 0.5, 3)}")

    print("\n  Poisson:")
    print(f"    rng.poisson(lam=5, size=3): {rng.poisson(5, 3)}")

    print("\n  Exponential:")
    print(f"    rng.exponential(scale=1, size=3): {rng.exponential(1, 3)}")

# Demo
print("\n=== Common Distributions ===")
distributions_demo()


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("np.random.RandomState CHECKLIST:")
print("=" * 60)
print("1. Always set seed for reproducibility: RandomState(42)")
print("2. Use keyword args for distribution params: normal(loc=, scale=)")
print("3. Parameter order: normal(mean, std) not normal(std, mean)!")
print("4. randint(low, high) - high is EXCLUSIVE")
print("5. rand(3,4) uses args, random((3,4)) uses tuple")
print("6. RandomState is stateful - each call changes state")
print("7. shuffle() modifies in-place, permutation() returns new array")
print("8. choice() default is WITH replacement")
print("9. Consider using np.random.default_rng() for new code")
print("10. Create fresh RandomState for reproducible functions")
