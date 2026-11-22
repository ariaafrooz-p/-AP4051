import unittest

from algebra import AlgebraicElement, Integer, Complex, Matrix, multiply


def M(text):
    return Matrix.make_matrix_from_string(text)


# ------------------------------ Part 1 ------------------------------------
class TestPart1(unittest.TestCase):
    def test_abstract_class_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            AlgebraicElement()

    def test_inheritance(self):
        for obj in (Integer(1), Complex(1, 2), M("1 2")):
            self.assertIsInstance(obj, AlgebraicElement)
        self.assertNotIsInstance(M("1"), (Integer, Complex))

    def test_sub_only_defined_in_base(self):
        for cls in (Integer, Complex, Matrix):
            self.assertNotIn("__sub__", cls.__dict__)
        self.assertIn("__sub__", AlgebraicElement.__dict__)

    def test_integer_arithmetic(self):
        self.assertEqual(Integer(3) + Integer(4), Integer(7))
        self.assertEqual(Integer(3) * Integer(4), Integer(12))
        self.assertEqual(-Integer(3), Integer(-3))
        self.assertEqual(Integer(8) - Integer(5), Integer(3))
        self.assertIsInstance(Integer(1) + Integer(2), Integer)

    def test_complex_arithmetic(self):
        self.assertEqual(Complex(1, 2) + Complex(3, -5), Complex(4, -3))
        self.assertEqual(Complex(1, 2) * Complex(3, 4), Complex(-5, 10))
        self.assertEqual(-Complex(1, -2), Complex(-1, 2))
        self.assertEqual(Complex(5, 5) - Complex(2, 7), Complex(3, -2))

    def test_mixed_integer_complex(self):
        r = Integer(3) + Complex(2, 1)
        self.assertIsInstance(r, Complex)
        self.assertEqual(r, Complex(5, 1))
        self.assertEqual(Integer(3) * Complex(2, 1), Complex(6, 3))
        self.assertEqual(Complex(2, 1) * Integer(3), Complex(6, 3))
        # result stays Complex even with zero imaginary part
        r = Complex(1, 1) * Complex(1, -1)
        self.assertIsInstance(r, Complex)
        self.assertEqual(r.imag, 0)

    def test_equality_across_types(self):
        self.assertTrue(Integer(3) == Complex(3, 0))
        self.assertTrue(Complex(3, 0) == Integer(3))
        self.assertFalse(Integer(3) == Complex(3, 1))
        self.assertFalse(Integer(3) == 3)

    def test_from_string(self):
        self.assertEqual(Integer.from_string("-12"), Integer(-12))
        self.assertEqual(Integer.from_string("+7"), Integer(7))
        self.assertEqual(Complex.from_string("5+2i"), Complex(5, 2))
        self.assertEqual(Complex.from_string("-3-4i"), Complex(-3, -4))
        self.assertEqual(Complex.from_string("0-2i"), Complex(0, -2))
        for bad in ("2i", "abc", "", "1.5", "1+i"):
            with self.assertRaises(ValueError):
                Complex.from_string(bad)
        for bad in ("", "1.5", "a", "--3"):
            with self.assertRaises(ValueError):
                Integer.from_string(bad)
        with self.assertRaises(TypeError):
            Integer.from_string(5)

    def test_constructor_validation_and_readonly(self):
        for bad in (True, 1.0, "1", None):
            with self.assertRaises(TypeError):
                Integer(bad)
        with self.assertRaises(TypeError):
            Complex(True, 1)
        with self.assertRaises(TypeError):
            Complex(1, 2.0)
        with self.assertRaises(AttributeError):
            Integer(1).value = 2
        with self.assertRaises(AttributeError):
            Complex(1, 2).real = 5

    def test_operands_not_modified(self):
        a, b = Complex(1, 2), Complex(3, 4)
        _ = a + b, a * b, -a, a - b
        self.assertEqual((a.real, a.imag, b.real, b.imag), (1, 2, 3, 4))


# ------------------------------ Part 2 ------------------------------------
class TestPart2(unittest.TestCase):
    def test_constructor_validation(self):
        one = Integer(1)
        with self.assertRaises(ValueError):
            Matrix(2, 2, [one] * 3)
        with self.assertRaises(ValueError):
            Matrix(0, 2, [])
        with self.assertRaises(TypeError):
            Matrix(1, 2, [one, 5])
        with self.assertRaises(TypeError):
            Matrix(1.0, 1, [one])
        with self.assertRaises(TypeError):
            Matrix(1, 1, "x")

    def test_encapsulation(self):
        source = [Integer(1), Integer(2)]
        m = Matrix(1, 2, source)
        source.append(Integer(99))
        source[0] = Integer(100)
        self.assertEqual(m.elements, (Integer(1), Integer(2)))
        self.assertIsInstance(m.elements, tuple)
        with self.assertRaises(AttributeError):
            m.rows = 5
        with self.assertRaises(AttributeError):
            m.elements = ()

    def test_row_major_order_and_mixed_elements(self):
        m = M("1 2 3; 4 5+2i 6")
        self.assertEqual((m.rows, m.cols), (2, 3))
        self.assertEqual(m.elements[4], Complex(5, 2))
        self.assertEqual(m.elements[3], Integer(4))

    def test_get_rows_and_cols(self):
        m = M("1 2 3; 4 5 6")
        self.assertEqual(Matrix.get_ith_row(m, 1),
                         [Integer(4), Integer(5), Integer(6)])
        self.assertEqual(Matrix.get_ith_col(m, 2), [Integer(3), Integer(6)])
        for bad in (-1, 2):
            with self.assertRaises(IndexError):
                Matrix.get_ith_row(m, bad)
        for bad in (-1, 3):
            with self.assertRaises(IndexError):
                Matrix.get_ith_col(m, bad)
        with self.assertRaises(TypeError):
            Matrix.get_ith_row([[1]], 0)

    def test_unit_matrix(self):
        u = Matrix.make_unit_matrix(3)
        self.assertEqual(u, M("1 0 0; 0 1 0; 0 0 1"))
        self.assertTrue(Matrix.is_unit_matrix(u))
        self.assertFalse(Matrix.is_unit_matrix(M("1 2; 3 4")))
        self.assertFalse(Matrix.is_unit_matrix(M("1 0 0; 0 1 0")))
        for bad in (0, -2):
            with self.assertRaises(ValueError):
                Matrix.make_unit_matrix(bad)
        with self.assertRaises(TypeError):
            Matrix.make_unit_matrix("3")
        with self.assertRaises(TypeError):
            Matrix.is_unit_matrix(5)

    def test_zero_matrix_with_complex_zero(self):
        self.assertTrue(Matrix.is_zero_matrix(M("0 0; 0+0i 0")))
        self.assertFalse(Matrix.is_zero_matrix(M("0 0; 0 1")))
        with self.assertRaises(TypeError):
            Matrix.is_zero_matrix("0")

    def test_triangular(self):
        upper = M("1 2 3; 0 4 5; 0 0 6")
        lower = M("1 0 0; 2 3 0; 4 5 6")
        self.assertTrue(Matrix.is_top_triangular_matrix(upper))
        self.assertFalse(Matrix.is_bottom_triangular_matrix(upper))
        self.assertTrue(Matrix.is_bottom_triangular_matrix(lower))
        self.assertFalse(Matrix.is_top_triangular_matrix(lower))
        zero = M("0 0; 0 0")
        self.assertTrue(Matrix.is_top_triangular_matrix(zero))
        self.assertTrue(Matrix.is_bottom_triangular_matrix(zero))
        rect = M("1 2 3; 0 4 5")
        self.assertFalse(Matrix.is_top_triangular_matrix(rect))
        self.assertFalse(Matrix.is_bottom_triangular_matrix(rect))

    def test_make_matrix_from_string_errors(self):
        for bad in ("", "   ", "1 2; 3", "1 2;", "1 x", "1 2i"):
            with self.assertRaises(ValueError, msg=bad):
                Matrix.make_matrix_from_string(bad)
        with self.assertRaises(TypeError):
            Matrix.make_matrix_from_string(None)

    def test_class_method_works_for_subclasses(self):
        class MyMatrix(Matrix):
            pass
        self.assertIsInstance(MyMatrix.make_matrix_from_string("1 2"),
                              MyMatrix)

    def test_equality(self):
        self.assertEqual(M("1 2; 3 4"), M("1 2; 3 4"))
        self.assertNotEqual(M("1 2; 3 4"), M("1 2; 3 5"))
        self.assertNotEqual(M("1 2 3 4"), M("1 2; 3 4"))
        self.assertNotEqual(M("1"), Integer(1))


# ------------------------------ Part 3 ------------------------------------
class TestPart3(unittest.TestCase):
    def test_matrix_addition(self):
        self.assertEqual(M("1 2; 3 4") + M("1 1; 1 1+1i"),
                         M("2 3; 4 5+1i"))
        with self.assertRaises(ValueError):
            M("1 2") + M("1; 2")

    def test_scalar_addition_both_orders(self):
        m = M("1 2; 3 4")
        self.assertEqual(m + Integer(2), M("3 4; 5 6"))
        self.assertEqual(Integer(2) + m, m + Integer(2))
        self.assertEqual(Complex(0, 1) + m, M("1+1i 2+1i; 3+1i 4+1i"))
        self.assertEqual(m + Complex(0, 1), Complex(0, 1) + m)

    def test_matrix_multiplication(self):
        m, n = M("1 2; 3 4"), M("2 0; 1 2")
        self.assertEqual(m * n, M("4 4; 10 8"))
        self.assertEqual(n * m, M("2 4; 7 10"))   # order matters
        self.assertNotEqual(m * n, n * m)
        self.assertEqual(M("1 2 3") * M("1; 2; 3"), M("14"))
        self.assertEqual(M("1; 2") * M("3 4"), M("3 4; 6 8"))
        with self.assertRaises(ValueError):
            M("1 2; 3 4") * M("1 2 3")

    def test_complex_matrix_multiplication(self):
        a = M("0+1i 1; 1 0")
        self.assertEqual(a * a, M("0 0+1i; 0+1i 1"))
        u = Matrix.make_unit_matrix(2)
        self.assertEqual(a * u, a)

    def test_scalar_multiplication_both_orders(self):
        m = M("1 2; 3 4")
        self.assertEqual(m * Integer(2), M("2 4; 6 8"))
        self.assertEqual(Integer(2) * m, m * Integer(2))
        self.assertEqual(Complex(0, 1) * m, m * Complex(0, 1))
        self.assertEqual(Complex(0, 1) * M("1"), M("0+1i"))

    def test_negation_and_subtraction(self):
        m, n = M("1 2; 3 4"), M("2 0; 1 2")
        self.assertEqual(-m, M("-1 -2; -3 -4"))
        self.assertEqual(m - n, M("-1 2; 2 2"))
        self.assertEqual(m - Integer(1), M("0 1; 2 3"))
        self.assertEqual(Integer(10) - m, M("9 8; 7 6"))
        self.assertEqual(Complex(1, 1) - M("1"), M("0+1i"))
        with self.assertRaises(ValueError):
            M("1 2") - M("1 2 3")

    def test_type_errors(self):
        m = M("1 2; 3 4")
        for bad in ("3", 3.0, 3, None, [1]):
            with self.assertRaises(TypeError):
                m + bad
            with self.assertRaises(TypeError):
                m * bad
            with self.assertRaises(TypeError):
                m - bad
            with self.assertRaises(TypeError):
                Integer(1) + bad
            with self.assertRaises(TypeError):
                Complex(1, 1) * bad
            with self.assertRaises(TypeError):
                Integer(1) - bad
        with self.assertRaises(TypeError):
            3 + m
        with self.assertRaises(TypeError):
            "3" * m

    def test_operands_not_modified(self):
        m, n = M("1 2; 3 4"), M("2 0; 1 2")
        _ = m + n, m * n, -m, m - n, m + Integer(1), Integer(2) * m
        self.assertEqual(m, M("1 2; 3 4"))
        self.assertEqual(n, M("2 0; 1 2"))

    def test_result_elements_are_algebraic_objects(self):
        r = M("1 2; 3 4") * M("1 0; 0 1")
        for e in r.elements:
            self.assertIsInstance(e, (Integer, Complex))
            self.assertNotIsInstance(e, int)

    def test_multiply_duck_typing(self):
        m = M("1 2; 3 4")
        self.assertEqual(multiply(m, Integer(2)), m * Integer(2))
        self.assertEqual(multiply(Integer(2), m), Integer(2) * m)
        self.assertEqual(multiply(Complex(1, 1), Complex(1, -1)),
                         Complex(2, 0))
        # works with any object supporting *, even built-ins
        self.assertEqual(multiply(3, 4), 12)
        self.assertEqual(multiply("ab", 2), "abab")
        with self.assertRaises(TypeError):
            multiply(m, "x")

    def test_spec_examples(self):
        x, y = Integer(3), Complex(2, 1)
        assert (x + y) == Complex(5, 1)
        assert (x * y) == Complex(6, 3)
        m, n = M("1 2; 3 4"), M("2 0; 1 2")
        assert (m * n) == M("4 4; 10 8")
        assert (Integer(2) + m) == (m + Integer(2))
        assert multiply(m, Integer(2)) == m * Integer(2)


if __name__ == "__main__":
    unittest.main()
