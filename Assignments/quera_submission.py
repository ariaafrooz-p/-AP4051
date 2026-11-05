"""SnapBox order allocation - single-file submission for Quera."""
import re
import sys
from decimal import Decimal


# ==================== validation.py ====================
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


# ==================== driver.py ====================
class Driver:
    """A delivery driver. All public attributes are read-only properties."""

    def __init__(self, username, position, service_category):
        self._username = validate_username(username)
        self._position = validate_position(position)
        self._service_category = validate_choice(service_category, CATEGORIES,
                                                 "service_category")
        self._credit = Decimal("0")
        self._status = "FREE"
        self._current_order = None

    @property
    def username(self):
        return self._username

    @property
    def position(self):
        return self._position

    @property
    def service_category(self):
        return self._service_category

    @property
    def credit(self):
        return self._credit

    @property
    def status(self):
        return self._status

    @property
    def current_order(self):
        return self._current_order

    def is_available(self):
        return self._status == "FREE"

    # ---- internal mutators (used by DeliverySystem only) ----
    def _take(self, order):
        self._status = "BUSY"
        self._current_order = order

    def _move_to(self, position):
        self._position = position

    def _add_credit(self, amount):
        self._credit += amount

    def _release(self):
        self._status = "FREE"
        self._current_order = None

    def __repr__(self):
        return f"Driver({self._username!r}, {self._position}, {self._service_category!r})"


# ==================== order.py ====================
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


# ==================== delivery_system.py ====================
_DRIVER_SHARE = Decimal("0.8")
_COMPANY_SHARE = Decimal("0.2")


class DeliverySystem:
    """Coordinates drivers and orders. Each instance has independent state."""

    def __init__(self):
        self._drivers = {}   # username -> Driver (insertion order = registration order)
        self._orders = {}    # order_id -> Order (insertion order = creation order)
        self._next_order_id = 1
        self._company_credit = Decimal("0")

    @property
    def company_credit(self):
        return self._company_credit

    @property
    def total_drivers(self):
        return len(self._drivers)

    # ------------------------------------------------------------ helpers
    def _driver(self, username):
        try:
            return self._drivers[username]
        except KeyError:
            raise KeyError(username) from None

    # ------------------------------------------------------------ commands
    def add_driver(self, username, position, service_category):
        validate_username(username)
        validate_position(position)
        validate_choice(service_category, CATEGORIES, "service_category")
        if username in self._drivers:
            return False
        self._drivers[username] = Driver(username, position, service_category)
        return True

    def create_order(self, service_category, starting_position, finishing_position):
        validate_choice(service_category, CATEGORIES, "service_category")
        validate_position(starting_position)
        validate_position(finishing_position)
        if starting_position == finishing_position:
            return None
        k = 1 + sum(1 for o in self._orders.values()
                    if o.is_pending() and o.service_category == service_category)
        d = manhattan(starting_position, finishing_position)
        cost = Decimal(100) * Decimal(k + d)
        order = Order(self._next_order_id, service_category,
                      starting_position, finishing_position, cost)
        self._orders[order.order_id] = order
        self._next_order_id += 1
        return order.order_id

    def assign_next_order(self, username):
        validate_username(username)
        driver = self._driver(username)
        if not driver.is_available():
            raise RuntimeError("driver is busy")
        best, best_dist = None, None
        for order in self._orders.values():
            if order.is_pending() and order.service_category == driver.service_category:
                dist = manhattan(driver.position, order.starting_position)
                if best is None or dist < best_dist:  # strict: older wins ties
                    best, best_dist = order, dist
        if best is None:
            return None
        best._set_status("ARRIVED")
        best._set_driver(driver)
        driver._take(best)
        return best.order_id

    def update_order_status(self, username, order_id, new_status):
        validate_username(username)
        validate_int(order_id, "order_id", 1)
        validate_choice(new_status, ORDER_STATUSES, "status")
        driver = self._driver(username)
        order = self._orders.get(order_id)
        if order is None or order.assigned_driver is not driver:
            return False
        if new_status == "PICKUP" and order.status == "ARRIVED":
            order._set_status("PICKUP")
            driver._move_to(order.starting_position)
            return True
        if new_status == "DELIVERED" and order.status == "PICKUP":
            order._set_status("DELIVERED")
            driver._move_to(order.finishing_position)
            driver._add_credit(order.cost * _DRIVER_SHARE)
            self._company_credit += order.cost * _COMPANY_SHARE
            driver._release()
            return True
        return False

    # ------------------------------------------------------------ queries
    def get_driver(self, username):
        validate_username(username)
        d = self._drivers.get(username)
        return None if d is None else (d.status, d.position, d.credit)

    def get_order(self, order_id):
        validate_int(order_id, "order_id", 1)
        o = self._orders.get(order_id)
        if o is None:
            return None
        name = None if o.assigned_driver is None else o.assigned_driver.username
        return (o.status, name, o.cost)

    def get_order_list(self, status):
        validate_choice(status, ORDER_STATUSES, "status")
        return [o.order_id for o in self._orders.values() if o.status == status]

    def get_driver_list(self, status):
        validate_choice(status, DRIVER_STATUSES, "status")
        return [d.username for d in self._drivers.values() if d.status == status]

    def get_near_drivers(self, position, count):
        validate_position(position)
        validate_int(count, "count", 0)
        free = [d for d in self._drivers.values() if d.is_available()]
        free.sort(key=lambda d: manhattan(d.position, position))  # stable sort
        return [d.username for d in free[:count]]

    def count_orders(self, position, distance, endpoint):
        validate_position(position)
        validate_int(distance, "distance", 0)
        validate_choice(endpoint, ENDPOINTS, "endpoint")
        attr = "starting_position" if endpoint == "START" else "finishing_position"
        return sum(1 for o in self._orders.values()
                   if manhattan(getattr(o, attr), position) <= distance)

    def get_nearest_pending_order(self, position):
        validate_position(position)
        best, best_dist = None, None
        for o in self._orders.values():
            if o.is_pending():
                dist = manhattan(o.starting_position, position)
                if best is None or dist < best_dist:
                    best, best_dist = o, dist
        return None if best is None else best.order_id

    def get_current_order_id(self, username):
        """Id of the order the driver is currently handling, or None."""
        validate_username(username)
        d = self._drivers.get(username)
        if d is None or d.current_order is None:
            return None
        return d.current_order.order_id

    def get_company_credit(self):
        return self._company_credit

    # ------------------------------------------------- creative feature: tips
    def add_tip(self, order_id, amount):
        """Give the driver of a DELIVERED order a tip (100% goes to the driver).

        Returns True on success; False if the order does not exist, is not
        DELIVERED, or the cumulative tips would exceed the order cost.
        Raises TypeError/ValueError for a non-Decimal / non-positive amount.
        """
        validate_int(order_id, "order_id", 1)
        if not isinstance(amount, Decimal):
            raise TypeError("amount must be a Decimal")
        if not amount > 0:
            raise ValueError("amount must be positive")
        order = self._orders.get(order_id)
        if order is None or order.status != "DELIVERED":
            return False
        if order.tip + amount > order.cost:
            return False
        order._add_tip(amount)
        order.assigned_driver._add_credit(amount)
        return True


# ==================== main.py ====================
_POS_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


def _none_or(value):
    return "None" if value is None else str(value)


def _join(items):
    return " ".join(items) if items else "None"


def _fmt_pos(p):
    return f"({p[0]}, {p[1]})"


def handle(system, line):
    """Execute one command line and return the output text ('' for END/blank)."""
    positions = [(int(x), int(y)) for x, y in _POS_RE.findall(line)]
    tokens = _POS_RE.sub("P", line).split()
    if not tokens:
        return ""
    cmd, a = tokens[0], tokens[1:]

    if cmd == "ADD-DRIVER":            # ADD-DRIVER user POS CATEGORY
        ok = system.add_driver(a[0], positions[0], a[2])
        return "user added successfully" if ok else "user previously added"

    if cmd == "CREATE-ORDER":          # CREATE-ORDER CATEGORY POS POS
        r = system.create_order(a[0], positions[0], positions[1])
        return "invalid order" if r is None else str(r)

    if cmd == "ASSIGN-NEXT-ORDER":     # ASSIGN-NEXT-ORDER user
        try:
            r = system.assign_next_order(a[0])
        except KeyError:
            return "invalid driver name"
        except RuntimeError:
            return "driver is already busy"
        return "there is no order right now" if r is None else f"{r} assigned to {a[0]}"

    if cmd == "GET-DRIVER":
        r = system.get_driver(a[0])
        if r is None:
            return "invalid driver name"
        return f"{r[0]} {_fmt_pos(r[1])} {int(r[2])}"

    if cmd == "ORDER-UPDATE":          # ORDER-UPDATE STATUS user order_id
        status, user, oid = a[0], a[1], int(a[2])
        if system.get_driver(user) is None:
            return "invalid driver name"
        if system.get_current_order_id(user) != oid:
            return "wrong order-id"
        try:
            ok = system.update_order_status(user, oid, status)
        except ValueError:
            ok = False
        return "status changed successfully" if ok else "invalid status"

    if cmd == "GET-ORDER":
        r = system.get_order(int(a[0]))
        if r is None:
            return "invalid order"
        return f"{r[0]} {_none_or(r[1])} {int(r[2])}"

    if cmd == "GET-ORDER-LIST":
        return _join([str(i) for i in system.get_order_list(a[0])])

    if cmd == "GET-DRIVER-LIST":
        return _join(system.get_driver_list(a[0]))

    if cmd == "GET-NEAR-DRIVER":       # GET-NEAR-DRIVER POS COUNT
        return _join(system.get_near_drivers(positions[0], int(a[1])))

    if cmd == "GET-CNT-ORDER":         # GET-CNT-ORDER POS DISTANCE START|FINISH
        return str(system.count_orders(positions[0], int(a[1]), a[2]))

    if cmd == "GET-NEAREST-PENDING-ORDER":
        return _none_or(system.get_nearest_pending_order(positions[0]))

    if cmd == "GET-COMPANY":
        return str(int(system.get_company_credit()))

    return ""  # END or unknown


def main(stream=None):
    stream = stream or sys.stdin
    system = DeliverySystem()
    for line in stream:
        if line.strip() == "END":
            break
        out = handle(system, line)
        if out:
            print(out)



if __name__ == "__main__":
    main()
