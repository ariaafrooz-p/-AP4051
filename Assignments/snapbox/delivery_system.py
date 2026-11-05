from decimal import Decimal

from driver import Driver
from order import Order
from validation import (CATEGORIES, DRIVER_STATUSES, ENDPOINTS, ORDER_STATUSES,
                        manhattan, validate_choice, validate_int,
                        validate_position, validate_username)

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
