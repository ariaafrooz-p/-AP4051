"""Shared input validation helpers (TypeError for wrong type, ValueError for bad value)."""
import re

CATEGORIES = ("BIKE", "VAN", "TRUCK")
DRIVER_STATUSES = ("FREE", "BUSY")
ORDER_STATUSES = ("PENDING", "ARRIVED", "PICKUP", "DELIVERED")
ENDPOINTS = ("START", "FINISH")
_USERNAME_RE = re.compile(r"[A-Za-z0-9]{1,25}")


def validate_int(value, name, minimum):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int")
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def validate_position(position):
    if not isinstance(position, tuple):
        raise TypeError("position must be a tuple")
    if len(position) != 2:
        raise ValueError("position must have exactly two coordinates")
    for c in position:
        if not isinstance(c, int) or isinstance(c, bool):
            raise TypeError("coordinates must be int")
    return position


def validate_choice(value, allowed, name):
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a str")
    if value not in allowed:
        raise ValueError(f"invalid {name}: {value!r}")
    return value


def validate_username(username):
    if not isinstance(username, str):
        raise TypeError("username must be a str")
    if _USERNAME_RE.fullmatch(username) is None:
        raise ValueError("username must be 1-25 English letters/digits")
    return username


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])
