import unittest
from decimal import Decimal

from order import Order


class TestOrder(unittest.TestCase):
    def make(self, **kw):
        args = dict(order_id=1, service_category="VAN", starting_position=(0, 0),
                    finishing_position=(2, 3), cost=Decimal("600"))
        args.update(kw)
        return Order(**args)

    def test_initial_values(self):
        o = self.make()
        self.assertEqual(o.status, "PENDING")
        self.assertIsNone(o.assigned_driver)
        self.assertTrue(o.is_pending())
        self.assertEqual(o.cost, Decimal("600"))

    def test_readonly(self):
        o = self.make()
        with self.assertRaises(AttributeError):
            o.cost = Decimal(1)
        with self.assertRaises(AttributeError):
            o.assigned_driver = None

    def test_invalid_id(self):
        with self.assertRaises(ValueError):
            self.make(order_id=0)
        with self.assertRaises(TypeError):
            self.make(order_id=True)

    def test_invalid_cost(self):
        with self.assertRaises(TypeError):
            self.make(cost=600)
        with self.assertRaises(ValueError):
            self.make(cost=Decimal(0))

    def test_invalid_position(self):
        with self.assertRaises(TypeError):
            self.make(starting_position=[0, 0])
        with self.assertRaises(ValueError):
            self.make(finishing_position=(1,))


if __name__ == "__main__":
    unittest.main()
