import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import unittest
from decimal import Decimal

from delivery_system import DeliverySystem


class TestTipFeature(unittest.TestCase):
    def setUp(self):
        self.s = DeliverySystem()
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (0, 4))   # cost 500

    def deliver(self):
        self.s.assign_next_order("a")
        self.s.update_order_status("a", 1, "PICKUP")
        self.s.update_order_status("a", 1, "DELIVERED")

    def test_tip_goes_fully_to_driver(self):
        self.deliver()
        self.assertTrue(self.s.add_tip(1, Decimal("50")))
        self.assertEqual(self.s.get_driver("a")[2], Decimal("450"))
        self.assertEqual(self.s.company_credit, Decimal("100"))

    def test_tip_rejected_before_delivery_or_unknown_order(self):
        self.assertFalse(self.s.add_tip(1, Decimal("10")))
        self.assertFalse(self.s.add_tip(42, Decimal("10")))
        self.assertEqual(self.s.get_driver("a")[2], Decimal("0"))

    def test_tip_limits_and_validation(self):
        self.deliver()
        self.assertTrue(self.s.add_tip(1, Decimal("300")))
        self.assertFalse(self.s.add_tip(1, Decimal("201")))   # 501 > cost 500
        with self.assertRaises(TypeError):
            self.s.add_tip(1, 10)
        with self.assertRaises(ValueError):
            self.s.add_tip(1, Decimal("-5"))


if __name__ == "__main__":
    unittest.main()
