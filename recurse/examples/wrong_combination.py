"""
Wrong Combination/Merge Errors

These functions recurse correctly but combine the results incorrectly.
The recursive calls return the right sub-results, but the merge step
has a bug that produces wrong final output.
"""


def merge_sort(arr):
    """Merge sort but the merge step is wrong.

    Bug: Merge doesn't properly interleave - just concatenates.
    Result: Array is split and rejoined but not actually sorted
    """
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    # Wrong merge: just concatenating instead of interleaving
    return left + right


# Corrected version:
# def merge_sort(arr):
#     if len(arr) <= 1:
#         return arr
#
#     mid = len(arr) // 2
#     left = merge_sort(arr[:mid])
#     right = merge_sort(arr[mid:])
#
#     # Proper merge
#     result = []
#     i = j = 0
#     while i < len(left) and j < len(right):
#         if left[i] <= right[j]:
#             result.append(left[i])
#             i += 1
#         else:
#             result.append(right[j])
#             j += 1
#     result.extend(left[i:])
#     result.extend(right[j:])
#     return result


def tree_sum(node):
    """Sum all values in a tree but wrong combination.

    Bug: Returns max of subtrees instead of sum.
    Result: Returns largest subtree sum, not total
    """
    if node is None:
        return 0

    left_sum = tree_sum(node.get('left'))
    right_sum = tree_sum(node.get('right'))

    # Wrong: using max instead of adding
    return node['value'] + max(left_sum, right_sum)


# Corrected version:
# def tree_sum(node):
#     if node is None:
#         return 0
#     left_sum = tree_sum(node.get('left'))
#     right_sum = tree_sum(node.get('right'))
#     return node['value'] + left_sum + right_sum


def count_nodes(node):
    """Count nodes in a tree but wrong combination.

    Bug: Only counts one subtree, not both.
    Result: Returns count of only the left branch
    """
    if node is None:
        return 0

    left_count = count_nodes(node.get('left'))
    right_count = count_nodes(node.get('right'))

    # Wrong: forgot to add right_count
    return 1 + left_count


# Corrected version:
# def count_nodes(node):
#     if node is None:
#         return 0
#     left_count = count_nodes(node.get('left'))
#     right_count = count_nodes(node.get('right'))
#     return 1 + left_count + right_count


def list_product(lst):
    """Multiply all elements but uses wrong operator.

    Bug: Uses addition instead of multiplication to combine.
    Result: Returns sum instead of product
    """
    if len(lst) == 0:
        return 1
    if len(lst) == 1:
        return lst[0]

    mid = len(lst) // 2
    left_product = list_product(lst[:mid])
    right_product = list_product(lst[mid:])

    # Wrong: adding instead of multiplying
    return left_product + right_product


# Corrected version:
# def list_product(lst):
#     if len(lst) == 0:
#         return 1
#     if len(lst) == 1:
#         return lst[0]
#     mid = len(lst) // 2
#     left_product = list_product(lst[:mid])
#     right_product = list_product(lst[mid:])
#     return left_product * right_product


def collect_leaves(node):
    """Collect all leaf values but wrong combination.

    Bug: Extends with single value instead of list from subtrees.
    Result: TypeError or wrong structure
    """
    if node is None:
        return []

    if node.get('left') is None and node.get('right') is None:
        return [node['value']]

    left_leaves = collect_leaves(node.get('left'))
    right_leaves = collect_leaves(node.get('right'))

    # Wrong: should return left_leaves + right_leaves
    return left_leaves.append(right_leaves)  # append returns None!


# Corrected version:
# def collect_leaves(node):
#     if node is None:
#         return []
#     if node.get('left') is None and node.get('right') is None:
#         return [node['value']]
#     left_leaves = collect_leaves(node.get('left'))
#     right_leaves = collect_leaves(node.get('right'))
#     return left_leaves + right_leaves


if __name__ == "__main__":
    print("Testing merge_sort([3, 1, 4, 1, 5, 9, 2, 6])...")
    print("Expected: [1, 1, 2, 3, 4, 5, 6, 9]")
    print(f"Got: {merge_sort([3, 1, 4, 1, 5, 9, 2, 6])}")

    print("\nTesting tree_sum...")
    tree = {
        'value': 1,
        'left': {
            'value': 2,
            'left': {'value': 4, 'left': None, 'right': None},
            'right': {'value': 5, 'left': None, 'right': None}
        },
        'right': {
            'value': 3,
            'left': None,
            'right': {'value': 6, 'left': None, 'right': None}
        }
    }
    print("Tree: 1 -> (2 -> 4, 5) and (3 -> 6)")
    print("Expected: 21 (1+2+3+4+5+6)")
    print(f"Got: {tree_sum(tree)}")

    print("\nTesting count_nodes on same tree...")
    print("Expected: 6")
    print(f"Got: {count_nodes(tree)}")

    print("\nTesting list_product([2, 3, 4])...")
    print("Expected: 24")
    print(f"Got: {list_product([2, 3, 4])}")

    print("\nTesting collect_leaves...")
    print("Expected: [4, 5, 6]")
    try:
        print(f"Got: {collect_leaves(tree)}")
    except (TypeError, AttributeError) as e:
        print(f"{type(e).__name__}: {e}")
