import re
from decimal import Decimal

# ---- shared validation helpers (TypeError: wrong type, ValueError: bad value)
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




class Order:
    """A delivery order. All public attributes are read-only properties."""

    def __init__(self, order_id, service_category, starting_position,
                 finishing_position, cost):
        self._order_id = validate_int(order_id, "order_id", 1)
        self._service_category = validate_choice(service_category, CATEGORIES,
                                                 "service_category")
        self._starting_position = validate_position(starting_position)
        self._finishing_position = validate_position(finishing_position)
        if not isinstance(cost, Decimal):
            raise TypeError("cost must be a Decimal")
        if not cost > 0:
            raise ValueError("cost must be positive")
        self._cost = cost
        self._status = "PENDING"
        self._assigned_driver = None
        self._tip = Decimal("0")

    @property
    def order_id(self):
        return self._order_id

    @property
    def service_category(self):
        return self._service_category

    @property
    def starting_position(self):
        return self._starting_position

    @property
    def finishing_position(self):
        return self._finishing_position

    @property
    def cost(self):
        return self._cost

    @property
    def status(self):
        return self._status

    @property
    def assigned_driver(self):
        return self._assigned_driver

    @property
    def tip(self):
        """Total tips received for this order (creative feature)."""
        return self._tip

    def is_pending(self):
        return self._status == "PENDING"

    # ---- internal mutators ----
    def _set_status(self, status):
        self._status = status

    def _set_driver(self, driver):
        self._assigned_driver = driver

    def _add_tip(self, amount):
        self._tip += amount

    def __repr__(self):
        return f"Order({self._order_id}, {self._status})"
