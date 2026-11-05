import unittest
from decimal import Decimal

from delivery_system import DeliverySystem
from driver import Driver
from order import Order


class ContractTest(unittest.TestCase):
    def setUp(self):
        self.s = DeliverySystem()

    def test_initial_state(self):
        self.assertEqual(self.s.total_drivers, 0)
        self.assertEqual(self.s.company_credit, Decimal("0"))

    def test_add_driver_and_duplicate(self):
        self.assertTrue(self.s.add_driver("ali", (0, 0), "BIKE"))
        self.assertFalse(self.s.add_driver("ali", (1, 1), "VAN"))
        self.assertEqual(self.s.total_drivers, 1)

    def test_order_cost_and_ids(self):
        self.assertEqual(self.s.create_order("BIKE", (0, 0), (1, 2)), 1)
        self.assertEqual(self.s.create_order("BIKE", (0, 0), (1, 2)), 2)
        self.assertEqual(self.s.get_order(1)[2], Decimal(400))
        self.assertEqual(self.s.get_order(2)[2], Decimal(500))
        self.assertIsNone(self.s.create_order("BIKE", (1, 1), (1, 1)))
        self.assertEqual(self.s.create_order("VAN", (0, 0), (0, 1)), 3)

    def test_full_cycle(self):
        self.s.add_driver("ali", (5, 5), "VAN")
        self.s.create_order("VAN", (0, 0), (0, 4))
        self.assertEqual(self.s.assign_next_order("ali"), 1)
        self.assertTrue(self.s.update_order_status("ali", 1, "PICKUP"))
        self.assertFalse(self.s.update_order_status("ali", 1, "PICKUP"))
        self.assertTrue(self.s.update_order_status("ali", 1, "DELIVERED"))
        self.assertEqual(self.s.get_driver("ali"), ("FREE", (0, 4), Decimal("400")))
        self.assertEqual(self.s.get_company_credit(), Decimal("100"))

    def test_errors(self):
        with self.assertRaises(TypeError):
            self.s.add_driver("a", [0, 0], "BIKE")
        with self.assertRaises(ValueError):
            self.s.add_driver("a", (0, 0), "CAR")
        with self.assertRaises(KeyError):
            self.s.assign_next_order("nobody")

    def test_read_only(self):
        d = Driver("x", (0, 0), "BIKE")
        with self.assertRaises(AttributeError):
            d.credit = Decimal(1)
        o = Order(1, "BIKE", (0, 0), (1, 1), Decimal(100))
        with self.assertRaises(AttributeError):
            o.status = "DELIVERED"


if __name__ == "__main__":
    unittest.main()
