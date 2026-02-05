"""
Wrong Order of Operations Errors

These functions process data in the wrong order relative to the recursive
call. Pre-order vs post-order matters for many algorithms, and doing
the work before vs after the recursive call produces different results.
"""


def print_countdown(n, results=None):
    """Print countdown but wrong order (counts up instead).

    Bug: Prints after recursion instead of before.
    Result: Prints 1, 2, 3, ... instead of n, n-1, n-2, ...
    """
    if results is None:
        results = []

    if n <= 0:
        return results

    # Wrong order: should print n first, then recurse
    print_countdown(n - 1, results)
    results.append(n)
    return results


# Corrected version:
# def print_countdown(n, results=None):
#     if results is None:
#         results = []
#     if n <= 0:
#         return results
#     results.append(n)  # Print first
#     print_countdown(n - 1, results)
#     return results


def build_string(chars):
    """Build string from chars but reversed due to order.

    Bug: Appends current char after recursive result.
    Result: String is reversed
    """
    if not chars:
        return ""

    # Wrong: puts current char at end instead of beginning
    return build_string(chars[1:]) + chars[0]


# Corrected version:
# def build_string(chars):
#     if not chars:
#         return ""
#     return chars[0] + build_string(chars[1:])


def inorder_traversal(node, result=None):
    """Inorder tree traversal but visits in wrong order.

    Bug: Visits node before left subtree (preorder instead of inorder).
    Result: Wrong traversal order
    """
    if result is None:
        result = []

    if node is None:
        return result

    # Wrong order: should be left, node, right
    result.append(node['value'])  # Visits too early
    inorder_traversal(node.get('left'), result)
    inorder_traversal(node.get('right'), result)

    return result


# Corrected version (inorder: left, node, right):
# def inorder_traversal(node, result=None):
#     if result is None:
#         result = []
#     if node is None:
#         return result
#     inorder_traversal(node.get('left'), result)
#     result.append(node['value'])
#     inorder_traversal(node.get('right'), result)
#     return result


def parse_nested_parens(s, depth=0):
    """Parse nested parentheses but processes close before open.

    Bug: Updates depth after recursive call instead of before.
    Result: Depth tracking is off by one
    """
    max_depth = depth

    for i, char in enumerate(s):
        if char == '(':
            # Wrong: should increment before recursing
            result = parse_nested_parens(s[i+1:], depth)
            depth += 1  # Too late!
            max_depth = max(max_depth, result)
        elif char == ')':
            depth -= 1

    return max_depth


# Corrected version:
# def parse_nested_parens(s):
#     depth = 0
#     max_depth = 0
#     for char in s:
#         if char == '(':
#             depth += 1
#             max_depth = max(max_depth, depth)
#         elif char == ')':
#             depth -= 1
#     return max_depth


def evaluate_postfix_recursive(tokens, stack=None):
    """Evaluate postfix expression but applies operator at wrong time.

    Bug: Pushes result before getting operands.
    Result: Wrong calculation order
    """
    if stack is None:
        stack = []

    if not tokens:
        return stack[-1] if stack else 0

    token = tokens[0]

    if token in ['+', '-', '*', '/']:
        # Wrong: should pop operands first, then compute
        result = 0  # Placeholder, will be wrong
        stack.append(result)
        b = stack.pop() if stack else 0  # Too late!
        a = stack.pop() if stack else 0

        if token == '+':
            result = a + b
    else:
        stack.append(int(token))

    return evaluate_postfix_recursive(tokens[1:], stack)


# Corrected version:
# def evaluate_postfix_recursive(tokens, stack=None):
#     if stack is None:
#         stack = []
#     if not tokens:
#         return stack[-1] if stack else 0
#     token = tokens[0]
#     if token in ['+', '-', '*', '/']:
#         b = stack.pop()  # Pop first
#         a = stack.pop()
#         if token == '+': result = a + b
#         elif token == '-': result = a - b
#         elif token == '*': result = a * b
#         else: result = a / b
#         stack.append(result)  # Then push
#     else:
#         stack.append(int(token))
#     return evaluate_postfix_recursive(tokens[1:], stack)


if __name__ == "__main__":
    print("Testing print_countdown(5)...")
    print("Expected: [5, 4, 3, 2, 1]")
    print(f"Got: {print_countdown(5)}")

    print("\nTesting build_string(['h', 'e', 'l', 'l', 'o'])...")
    print("Expected: 'hello'")
    print(f"Got: '{build_string(['h', 'e', 'l', 'l', 'o'])}'")

    print("\nTesting inorder_traversal on BST...")
    #       4
    #      / \
    #     2   6
    #    / \ / \
    #   1  3 5  7
    bst = {
        'value': 4,
        'left': {
            'value': 2,
            'left': {'value': 1, 'left': None, 'right': None},
            'right': {'value': 3, 'left': None, 'right': None}
        },
        'right': {
            'value': 6,
            'left': {'value': 5, 'left': None, 'right': None},
            'right': {'value': 7, 'left': None, 'right': None}
        }
    }
    print("Expected (inorder): [1, 2, 3, 4, 5, 6, 7]")
    print(f"Got: {inorder_traversal(bst)}")

    print("\nTesting parse_nested_parens('((()))')...")
    print("Expected max depth: 3")
    print(f"Got: {parse_nested_parens('((()))')}")
