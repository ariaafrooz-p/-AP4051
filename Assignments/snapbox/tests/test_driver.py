import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import unittest
from decimal import Decimal

from driver import Driver


class TestDriver(unittest.TestCase):
    def test_initial_values(self):
        d = Driver("Ali1", (1, 2), "TRUCK")
        self.assertEqual((d.username, d.position, d.service_category),
                         ("Ali1", (1, 2), "TRUCK"))
        self.assertEqual(d.credit, Decimal("0"))
        self.assertEqual(d.status, "FREE")
        self.assertIsNone(d.current_order)
        self.assertTrue(d.is_available())

    def test_readonly_properties(self):
        d = Driver("a", (0, 0), "BIKE")
        for name, val in [("username", "b"), ("position", (1, 1)), ("status", "BUSY"),
                          ("current_order", None), ("service_category", "VAN")]:
            with self.assertRaises(AttributeError):
                setattr(d, name, val)

    def test_invalid_inputs(self):
        with self.assertRaises(TypeError):
            Driver(5, (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            Driver("", (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            Driver("a" * 26, (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            Driver("a_b", (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            Driver("a", (0, 0, 0), "BIKE")
        with self.assertRaises(TypeError):
            Driver("a", (True, 0), "BIKE")
        with self.assertRaises(ValueError):
            Driver("a", (0, 0), "bike")


if __name__ == "__main__":
    unittest.main()
