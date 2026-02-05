"""
Mutating Shared State Errors

These functions pass mutable objects (like lists) and modify them
during recursion. Changes made in one recursive branch affect other
branches, leading to incorrect results.
"""


def find_all_paths(graph, start, end, path=[]):
    """Find all paths in a graph but mutates the shared path list.

    Bug: Default mutable argument and in-place append corrupt paths.
    Result: Paths from different branches get mixed together
    """
    path.append(start)  # Mutates the shared list

    if start == end:
        return [path]  # Returns reference to the same mutated list

    if start not in graph:
        return []

    paths = []
    for node in graph[start]:
        if node not in path:
            new_paths = find_all_paths(graph, node, end, path)
            paths.extend(new_paths)

    return paths


# Corrected version:
# def find_all_paths(graph, start, end, path=None):
#     if path is None:
#         path = []
#     path = path + [start]  # Create new list instead of mutating
#
#     if start == end:
#         return [path]
#
#     if start not in graph:
#         return []
#
#     paths = []
#     for node in graph[start]:
#         if node not in path:
#             new_paths = find_all_paths(graph, node, end, path)
#             paths.extend(new_paths)
#     return paths


def generate_subsets(nums, index=0, current=[]):
    """Generate all subsets but mutates the current list.

    Bug: Appends and pops from shared 'current' list, but the collected
    subsets are all references to the same list.
    Result: All subsets end up being empty or identical
    """
    result = []

    if index == len(nums):
        result.append(current)  # Appends reference to mutating list
        return result

    # Include current element
    current.append(nums[index])
    result.extend(generate_subsets(nums, index + 1, current))

    # Exclude current element (backtrack)
    current.pop()
    result.extend(generate_subsets(nums, index + 1, current))

    return result


# Corrected version:
# def generate_subsets(nums, index=0, current=None):
#     if current is None:
#         current = []
#
#     if index == len(nums):
#         return [current[:]]  # Return a copy
#
#     result = []
#     # Include current element
#     result.extend(generate_subsets(nums, index + 1, current + [nums[index]]))
#     # Exclude current element
#     result.extend(generate_subsets(nums, index + 1, current))
#     return result


def flatten_nested(nested, result=[]):
    """Flatten a nested list but uses mutable default and shared result.

    Bug: Default mutable argument accumulates across multiple calls.
    Result: Calling function multiple times keeps adding to same list
    """
    for item in nested:
        if isinstance(item, list):
            flatten_nested(item, result)
        else:
            result.append(item)
    return result


# Corrected version:
# def flatten_nested(nested, result=None):
#     if result is None:
#         result = []
#     for item in nested:
#         if isinstance(item, list):
#             flatten_nested(item, result)
#         else:
#             result.append(item)
#     return result


if __name__ == "__main__":
    print("Testing find_all_paths...")
    graph = {
        'A': ['B', 'C'],
        'B': ['D'],
        'C': ['D'],
        'D': []
    }
    print("Graph: A->B->D, A->C->D")
    print("Expected: [['A', 'B', 'D'], ['A', 'C', 'D']]")
    paths = find_all_paths(graph, 'A', 'D')
    print(f"Got: {paths}")

    print("\nTesting generate_subsets([1, 2])...")
    print("Expected: [[], [2], [1], [1, 2]]")
    subsets = generate_subsets([1, 2])
    print(f"Got: {subsets}")

    print("\nTesting flatten_nested multiple times...")
    print("First call: flatten_nested([1, [2, 3]])")
    result1 = flatten_nested([1, [2, 3]])
    print(f"Got: {result1}")
    print("Second call: flatten_nested([4, 5])")
    result2 = flatten_nested([4, 5])
    print(f"Expected: [4, 5]")
    print(f"Got: {result2}")  # Will include elements from first call!
