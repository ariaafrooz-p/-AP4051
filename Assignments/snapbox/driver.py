from decimal import Decimal

from order import (CATEGORIES, validate_choice, validate_position,
                   validate_username)


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
