"""
NamedTuple Gotchas
==================
These errors are NOT caught by static analyzers because NamedTuples accept
positional arguments and support indexing, making wrong usage syntactically valid.
"""

from collections import namedtuple
from typing import NamedTuple


# =============================================================================
# 1. Wrong Field Order
# =============================================================================

# Define a Point with x, y order
Point = namedtuple('Point', ['x', 'y'])

def create_point_bad(x_val, y_val):
    """BAD: Arguments in wrong order (y, x instead of x, y)"""
    return Point(y_val, x_val)  # Swapped! But syntactically valid

def create_point_good(x_val, y_val):
    """GOOD: Use keyword arguments to be explicit"""
    return Point(x=x_val, y=y_val)

# Demo
print("=== Wrong Field Order ===")
p_bad = create_point_bad(10, 20)
p_good = create_point_good(10, 20)

print(f"Intended: x=10, y=20")
print(f"BAD:  p.x={p_bad.x}, p.y={p_bad.y}")   # p.x=20, p.y=10 (swapped!)
print(f"GOOD: p.x={p_good.x}, p.y={p_good.y}")  # p.x=10, p.y=20


# =============================================================================
# 2. Immutability Forgotten
# =============================================================================

def modify_point_bad(point):
    """BAD: Trying to modify immutable NamedTuple"""
    try:
        point.x = 100  # This will raise AttributeError!
    except AttributeError as e:
        print(f"  AttributeError: {e}")
    return point

def modify_point_good(point):
    """GOOD: Use _replace() to create modified copy"""
    return point._replace(x=100)

# Demo
print("\n=== Immutability ===")
p = Point(1, 2)
print(f"Original: {p}")
print("Trying to modify x to 100:")
print(f"BAD (direct assignment):")
p_bad = modify_point_bad(p)
print(f"  Result: {p_bad}")  # Unchanged

print(f"GOOD (_replace):")
p_good = modify_point_good(p)
print(f"  Result: {p_good}")  # Point(x=100, y=2)


# =============================================================================
# 3. Accessing by Wrong Index
# =============================================================================

Rectangle = namedtuple('Rectangle', ['width', 'height'])

def get_area_bad(rect):
    """BAD: Using wrong indices"""
    # Forgot which index is which
    return rect[1] * rect[1]  # height * height (wrong!)

def get_area_good(rect):
    """GOOD: Use named attributes"""
    return rect.width * rect.height

# Demo
print("\n=== Wrong Index Access ===")
rect = Rectangle(width=10, height=5)
print(f"Rectangle: width={rect.width}, height={rect.height}")
print(f"BAD (rect[1] * rect[1]): {get_area_bad(rect)}")   # 25 (5*5, wrong!)
print(f"GOOD (width * height): {get_area_good(rect)}")     # 50


# =============================================================================
# 4. _replace() Returns New Object
# =============================================================================

def update_point_bad(point, new_x):
    """BAD: Forgetting that _replace returns a NEW object"""
    point._replace(x=new_x)  # Result is discarded!
    return point  # Returns original, unchanged

def update_point_good(point, new_x):
    """GOOD: Use the returned object"""
    return point._replace(x=new_x)

# Demo
print("\n=== _replace() Returns New Object ===")
p = Point(1, 2)
print(f"Original: {p}")

p_bad = update_point_bad(p, 100)
print(f"BAD (discarded _replace): {p_bad}")  # Point(x=1, y=2) - unchanged!

p_good = update_point_good(p, 100)
print(f"GOOD (used return value): {p_good}")  # Point(x=100, y=2)


# =============================================================================
# 5. Unpacking Order Confusion
# =============================================================================

Person = namedtuple('Person', ['name', 'age', 'city'])

def process_person_bad():
    """BAD: Unpacking in wrong order"""
    person = Person('Alice', 30, 'NYC')
    age, name, city = person  # Wrong order!
    return f"{name} is {age} years old"

def process_person_good():
    """GOOD: Use named access or correct order"""
    person = Person('Alice', 30, 'NYC')
    name, age, city = person  # Correct order
    return f"{name} is {age} years old"

def process_person_best():
    """BEST: Use named attributes - no order confusion possible"""
    person = Person('Alice', 30, 'NYC')
    return f"{person.name} is {person.age} years old"

# Demo
print("\n=== Unpacking Order ===")
print(f"BAD (wrong order): {process_person_bad()}")    # "30 is Alice years old"
print(f"GOOD (correct order): {process_person_good()}")  # "Alice is 30 years old"
print(f"BEST (named access): {process_person_best()}")   # "Alice is 30 years old"


# =============================================================================
# 6. Default Values Gotcha
# =============================================================================

# Old-style namedtuple - no default values directly
PointOld = namedtuple('PointOld', ['x', 'y'])

# New-style with defaults (Python 3.7+)
PointWithDefaults = namedtuple('PointWithDefaults', ['x', 'y'], defaults=[0])
# Note: defaults apply to RIGHTMOST fields!

# Demo
print("\n=== Default Values ===")
try:
    p1 = PointOld(1)  # Missing y!
except TypeError as e:
    print(f"PointOld(1) raises: {e}")

# With defaults
p2 = PointWithDefaults(1)  # y defaults to 0
print(f"PointWithDefaults(1): x={p2.x}, y={p2.y}")

# Common mistake: thinking defaults apply left-to-right
# PointWithDefaults = namedtuple('Point', ['x', 'y'], defaults=[0, 0])
# means BOTH have defaults, with x=0, y=0 as defaults
PointBothDefaults = namedtuple('PointBothDefaults', ['x', 'y'], defaults=[0, 0])
p3 = PointBothDefaults()
print(f"PointBothDefaults(): x={p3.x}, y={p3.y}")


# =============================================================================
# 7. Typed NamedTuple (Python 3.6+)
# =============================================================================

class TypedPoint(NamedTuple):
    """BETTER: Use typing.NamedTuple for type hints"""
    x: float
    y: float
    label: str = "origin"  # Default value

# Demo
print("\n=== Typed NamedTuple ===")
tp = TypedPoint(1.0, 2.0)
print(f"TypedPoint(1.0, 2.0): {tp}")
print(f"  label defaults to: {tp.label}")

tp2 = TypedPoint(x=3.0, y=4.0, label="point A")
print(f"TypedPoint with label: {tp2}")


# =============================================================================
# 8. Comparison Pitfall
# =============================================================================

PointA = namedtuple('Point', ['x', 'y'])
PointB = namedtuple('Point', ['x', 'y'])  # Same name, different type!

def compare_points_bad():
    """Surprising: NamedTuples with same values are equal even if different types"""
    p1 = PointA(1, 2)
    p2 = PointB(1, 2)
    return p1 == p2  # True! (compares as tuples)

# Demo
print("\n=== Comparison Pitfall ===")
p1 = PointA(1, 2)
p2 = PointB(1, 2)
p3 = (1, 2)  # Plain tuple

print(f"PointA(1,2) == PointB(1,2): {p1 == p2}")  # True
print(f"PointA(1,2) == (1, 2): {p1 == p3}")       # True
print(f"type(PointA) == type(PointB): {type(p1) == type(p2)}")  # False!


# =============================================================================
# 9. _asdict() Returns Regular Dict
# =============================================================================

def to_json_bad(point):
    """Note: _asdict() returns a regular dict (not OrderedDict in 3.8+)"""
    d = point._asdict()
    # Can modify the dict (doesn't affect original tuple)
    d['x'] = 999
    return d, point

# Demo
print("\n=== _asdict() Behavior ===")
p = Point(1, 2)
d, p_after = to_json_bad(p)
print(f"Dict after modification: {d}")  # {'x': 999, 'y': 2}
print(f"Original point unchanged: {p_after}")  # Point(x=1, y=2)


# =============================================================================
# Summary
# =============================================================================
print("\n" + "=" * 60)
print("NAMEDTUPLE CHECKLIST:")
print("=" * 60)
print("1. Use KEYWORD arguments: Point(x=1, y=2) not Point(1, 2)")
print("2. NamedTuples are IMMUTABLE - use _replace() for 'updates'")
print("3. _replace() RETURNS a new object - don't discard it!")
print("4. Use named attributes (p.x) instead of indices (p[0])")
print("5. Be careful with unpacking order")
print("6. Consider typing.NamedTuple for type hints and defaults")
print("7. Remember: comparison is by VALUE, not by type")
