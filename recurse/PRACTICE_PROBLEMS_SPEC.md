# Recursion Debugging Practice Problems Specification

## Context

This directory contains a `trace` decorator (`trace.py`) for debugging recursive functions. The goal is to generate practice problems with intentional bugs so the user can practice:
1. Identifying the bug type from trace output
2. Locating the exact line causing the issue
3. Fixing the bug

## The Trace Decorator

```python
from trace import trace

@trace
def my_recursive_func(n):
    ...
```

The decorator prints each call with indentation showing depth, and return values with `└─>`. It handles NamedTuples, class instances, NumPy arrays, and dicts intelligently.

Key options:
- `max_depth=N` - limit output depth
- `watch=[0,2]` - only show args at certain positions
- `show_depth=True` - prefix with `[0]`, `[1]`, etc.

## Bug Patterns to Generate

### 1. Missing Base Case
The function never stops recursing.

**What it looks like in trace:**
- Arguments keep decreasing/changing past the expected stop point
- Eventually hits RecursionError

**Example pattern:**
```python
def factorial(n):
    return n * factorial(n - 1)  # No base case for n <= 1
```

---

### 2. Wrong Base Case Value
Base case exists but returns wrong value.

**What it looks like in trace:**
- Recursion stops at the right depth
- Base case returns wrong value (often 0 instead of 1, or vice versa)
- Wrong value propagates up through all returns

**Example pattern:**
```python
def factorial(n):
    if n <= 1:
        return 0  # Should be 1
    return n * factorial(n - 1)
```

---

### 3. Not Reducing Toward Base Case
Recursive call doesn't make progress.

**What it looks like in trace:**
- Same arguments appear repeatedly
- RecursionError eventually

**Example pattern:**
```python
def find_element(lst, target, idx=0):
    if idx >= len(lst): return -1
    if lst[idx] == target: return idx
    return find_element(lst, target, idx)  # Should be idx + 1
```

---

### 4. Forgetting Return Statement
Recursive call made but result not returned.

**What it looks like in trace:**
- Recursion proceeds correctly
- Then a return shows `None`
- TypeError when trying to use None

**Example pattern:**
```python
def sum_to_n(n):
    if n <= 0: return 0
    sum_to_n(n - 1) + n  # Missing return!
```

---

### 5. Wrong Argument Reduction
Reducing argument wrong way (off-by-one, wrong slice, etc.)

**What it looks like in trace:**
- Arguments change but in wrong pattern
- May cause infinite recursion or wrong result
- Empty arrays/lists may appear unexpectedly

**Example pattern:**
```python
def reverse(lst):
    if len(lst) <= 1: return lst
    return [lst[0]] + reverse(lst[1:])  # Should be [lst[-1]] + reverse(lst[:-1])
```

---

### 6. Only Processing One Branch
In tree/graph recursion, only one child is processed.

**What it looks like in trace:**
- Path always goes one direction (all left, or all right)
- Nodes on other side never visited

**Example pattern:**
```python
def tree_find(node, target):
    if node is None: return False
    if node.value == target: return True
    return tree_find(node.left, target)  # Never checks right!
```

---

### 7. Wrong Combination/Merge
Recursive calls correct but combining results wrong.

**What it looks like in trace:**
- Subtree results are correct
- Final combination is wrong (sum vs max, + vs *, etc.)

**Example pattern:**
```python
def tree_sum(node):
    if node is None: return 0
    left = tree_sum(node.left)
    right = tree_sum(node.right)
    return node.value + max(left, right)  # Should be left + right
```

---

### 8. Wrong Order of Operations
Processing node before/after recursive call matters.

**What it looks like in trace:**
- Values appear in wrong order in accumulated results
- Preorder when inorder expected, etc.

**Example pattern:**
```python
def inorder(node):
    if node is None: return []
    return [node.value] + inorder(node.left) + inorder(node.right)  # Preorder!
    # Should be: inorder(node.left) + [node.value] + inorder(node.right)
```

---

### 9. Accumulator Mistakes

#### 9a. Not passing accumulator
```python
def factorial_acc(n, acc=1):
    if n <= 1: return acc
    return factorial_acc(n - 1)  # Forgot to pass acc * n
```

#### 9b. Resetting accumulator
```python
def sum_list(lst, acc=0):
    if not lst: return acc
    acc = 0  # Resets every call!
    return sum_list(lst[1:], acc + lst[0])
```

#### 9c. Wrong initial value
```python
def count_items(lst, acc=1):  # Should start at 0
    ...
```

**What it looks like in trace:**
- Accumulator values don't grow as expected
- Or accumulator resets to same value each call

---

### 10. Mutable Default Argument
Using `[]` or `{}` as default accumulates across calls.

**What it looks like in trace:**
- First call looks correct
- Second call shows accumulated state from first call

**Example pattern:**
```python
def collect(node, result=[]):  # Mutable default!
    if node is None: return result
    result.append(node.value)
    ...
```

---

### 11. NumPy-Specific Issues

#### 11a. Identity vs equality
```python
if arr[idx] is target:  # Should be ==
```

#### 11b. Wrong empty array handling
```python
if len(arr) == 0:
    return 0  # Might need float('-inf') for max, or different value
```

---

### 12. Class Method Issues
When recursion is in a class method:
- Forgetting `self` in recursive call
- Not passing updated state correctly

---

## Practice Problem Format

Each practice problem should:

1. **Provide a buggy function** with exactly one bug from the patterns above
2. **Include a test case** that reveals the bug
3. **State expected vs actual behavior**
4. **Suggest using `@trace` with appropriate options**

The user should:
1. Add `@trace` decorator
2. Run the test case
3. Identify the bug from the trace output
4. Fix the bug

## Data Structures to Use

- **NamedTuple trees**: `Node = namedtuple('Node', ['value', 'left', 'right'])`
- **NumPy arrays**: For divide-and-conquer patterns
- **Classes with recursive methods**: Tokenizers, analyzers, etc.
- **Lists**: For accumulator patterns
- **Dicts**: For tree-like structures

## Difficulty Progression

1. **Easy**: Single obvious bug, simple data structure (factorial, sum)
2. **Medium**: Tree structures, NamedTuples, multiple recursive calls
3. **Hard**: Class methods, NumPy arrays, subtle bugs like mutable defaults
