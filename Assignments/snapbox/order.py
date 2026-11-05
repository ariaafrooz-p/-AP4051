from decimal import Decimal

from validation import (CATEGORIES, validate_choice, validate_int,
                        validate_position)


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
