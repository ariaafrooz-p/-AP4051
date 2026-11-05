import unittest
from decimal import Decimal

from delivery_system import DeliverySystem


class TestDeliverySystem(unittest.TestCase):
    def setUp(self):
        self.s = DeliverySystem()

    def test_systems_are_independent(self):
        other = DeliverySystem()
        self.s.add_driver("a", (0, 0), "BIKE")
        self.assertEqual(other.total_drivers, 0)

    def test_duplicate_username_case_sensitive(self):
        self.assertTrue(self.s.add_driver("Ali", (0, 0), "BIKE"))
        self.assertTrue(self.s.add_driver("ali", (0, 0), "BIKE"))
        self.assertEqual(self.s.total_drivers, 2)

    def test_failed_create_does_not_use_id(self):
        self.assertIsNone(self.s.create_order("BIKE", (3, 3), (3, 3)))
        self.assertEqual(self.s.create_order("BIKE", (0, 0), (0, 1)), 1)

    def test_cost_counts_pending_same_category(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (0, 1))      # k=1 -> 200
        self.s.create_order("BIKE", (0, 0), (0, 1))      # k=2 -> 300
        self.s.assign_next_order("a")                    # order 1 no longer pending
        self.s.create_order("BIKE", (0, 0), (0, 1))      # k=2 -> 300
        self.assertEqual([self.s.get_order(i)[2] for i in (1, 2, 3)],
                         [Decimal(200), Decimal(300), Decimal(300)])

    def test_assign_nearest_and_tie_break(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("BIKE", (5, 5), (6, 6))   # 1, dist 10
        self.s.create_order("BIKE", (1, 1), (6, 6))   # 2, dist 2
        self.s.create_order("BIKE", (2, 0), (6, 6))   # 3, dist 2 (tie, newer)
        self.assertEqual(self.s.assign_next_order("a"), 2)

    def test_assign_ignores_other_categories(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("VAN", (0, 0), (1, 1))
        self.assertIsNone(self.s.assign_next_order("a"))

    def test_assign_busy_raises_and_unknown_keyerror(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (1, 1))
        self.s.create_order("BIKE", (0, 0), (1, 1))
        self.s.assign_next_order("a")
        with self.assertRaises(RuntimeError):
            self.s.assign_next_order("a")
        with self.assertRaises(KeyError):
            self.s.assign_next_order("zzz")
        self.assertEqual(self.s.get_order_list("PENDING"), [2])

    def test_status_chain_and_positions(self):
        self.s.add_driver("a", (9, 9), "BIKE")
        self.s.create_order("BIKE", (1, 1), (4, 5))
        self.s.assign_next_order("a")
        self.assertEqual(self.s.get_driver("a")[0], "BUSY")
        self.assertEqual(self.s.get_driver("a")[1], (9, 9))
        self.assertFalse(self.s.update_order_status("a", 1, "DELIVERED"))  # skip
        self.assertTrue(self.s.update_order_status("a", 1, "PICKUP"))
        self.assertEqual(self.s.get_driver("a")[1], (1, 1))
        self.assertTrue(self.s.update_order_status("a", 1, "DELIVERED"))
        self.assertEqual(self.s.get_driver("a")[1], (4, 5))
        self.assertFalse(self.s.update_order_status("a", 1, "DELIVERED"))  # repeat

    def test_payment_split(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (0, 4))   # 500
        self.s.assign_next_order("a")
        self.s.update_order_status("a", 1, "PICKUP")
        self.s.update_order_status("a", 1, "DELIVERED")
        self.assertEqual(self.s.get_driver("a")[2], Decimal("400"))
        self.assertEqual(self.s.company_credit, Decimal("100"))
        self.assertEqual(self.s.get_order(1), ("DELIVERED", "a", Decimal(500)))

    def test_other_drivers_order_rejected(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        self.s.add_driver("b", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (1, 1))
        self.s.assign_next_order("a")
        self.assertFalse(self.s.update_order_status("b", 1, "PICKUP"))
        self.assertEqual(self.s.get_order(1)[0], "ARRIVED")

    def test_update_invalid_status_and_unknown_driver(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            self.s.update_order_status("a", 1, "DONE")
        with self.assertRaises(KeyError):
            self.s.update_order_status("x", 1, "PICKUP")
        self.assertFalse(self.s.update_order_status("a", 99, "PICKUP"))

    def test_get_queries_missing(self):
        self.assertIsNone(self.s.get_driver("nope"))
        self.assertIsNone(self.s.get_order(5))
        self.assertEqual(self.s.get_order_list("PENDING"), [])
        self.assertEqual(self.s.get_driver_list("FREE"), [])
        self.s.create_order("BIKE", (0, 0), (1, 1))
        self.assertEqual(self.s.get_order(1)[1], None)

    def test_lists_keep_registration_order(self):
        for n in ("c", "a", "b"):
            self.s.add_driver(n, (0, 0), "BIKE")
        self.assertEqual(self.s.get_driver_list("FREE"), ["c", "a", "b"])

    def test_near_drivers(self):
        self.s.add_driver("far", (9, 9), "BIKE")
        self.s.add_driver("t1", (1, 0), "VAN")
        self.s.add_driver("t2", (0, 1), "BIKE")
        self.s.add_driver("busy", (0, 0), "BIKE")
        self.s.create_order("BIKE", (0, 0), (1, 1))
        self.s.assign_next_order("busy")   # nearest bike -> busy takes it
        self.assertEqual(self.s.get_near_drivers((0, 0), 2), ["t1", "t2"])
        self.assertEqual(self.s.get_near_drivers((0, 0), 0), [])
        self.assertEqual(len(self.s.get_near_drivers((0, 0), 100)), 3)

    def test_count_orders_inclusive(self):
        self.s.create_order("BIKE", (0, 0), (5, 5))
        self.s.create_order("VAN", (3, 0), (0, 0))
        self.assertEqual(self.s.count_orders((0, 0), 3, "START"), 2)
        self.assertEqual(self.s.count_orders((0, 0), 2, "START"), 1)
        self.assertEqual(self.s.count_orders((0, 0), 0, "FINISH"), 1)
        with self.assertRaises(ValueError):
            self.s.count_orders((0, 0), 1, "MIDDLE")
        with self.assertRaises(ValueError):
            self.s.count_orders((0, 0), -1, "START")

    def test_nearest_pending(self):
        self.assertIsNone(self.s.get_nearest_pending_order((0, 0)))
        self.s.create_order("BIKE", (4, 0), (9, 9))
        self.s.create_order("VAN", (0, 4), (9, 9))   # tie -> older
        self.assertEqual(self.s.get_nearest_pending_order((0, 0)), 1)

    def test_validation_types(self):
        with self.assertRaises(TypeError):
            self.s.get_near_drivers((0, 0), True)
        with self.assertRaises(TypeError):
            self.s.get_order("1")
        with self.assertRaises(ValueError):
            self.s.get_order(0)
        with self.assertRaises(TypeError):
            self.s.get_order_list(None)

    def test_failed_ops_do_not_change_state(self):
        self.s.add_driver("a", (0, 0), "BIKE")
        with self.assertRaises(ValueError):
            self.s.create_order("CAR", (0, 0), (1, 1))
        self.assertEqual(self.s.get_order_list("PENDING"), [])
        self.assertEqual(self.s.create_order("BIKE", (0, 0), (1, 1)), 1)


if __name__ == "__main__":
    unittest.main()
