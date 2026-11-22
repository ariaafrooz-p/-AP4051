"""Numeric and matrix algebra library: Integer, Complex and Matrix.

All three concrete types inherit from the abstract AlgebraicElement, which
defines the shared contract (+, *, unary -) and implements subtraction once.
"""
import re
from abc import ABC, abstractmethod


def _is_int(value):
    """True for a real int (bool is rejected)."""
    return isinstance(value, int) and not isinstance(value, bool)


# --------------------------------------------------------------------------
# Part 1: abstract base class and numeric types
# --------------------------------------------------------------------------
class AlgebraicElement(ABC):
    """Common contract: addition, multiplication and additive inverse."""

    @abstractmethod
    def __add__(self, other):
        ...

    @abstractmethod
    def __mul__(self, other):
        ...

    @abstractmethod
    def __neg__(self):
        ...

    def __sub__(self, other):
        # Implemented only here; subclasses reuse it via inheritance.
        if not isinstance(other, AlgebraicElement):
            raise TypeError(
                f"unsupported operand type for -: {type(other).__name__}")
        return self + (-other)


class Integer(AlgebraicElement):
    _PATTERN = re.compile(r"[+-]?[0-9]+")

    def __init__(self, value: int):
        if not _is_int(value):
            raise TypeError("Integer value must be an int")
        self.__value = value

    @property
    def value(self) -> int:
        return self.__value

    @classmethod
    def from_string(cls, text: str):
        if not isinstance(text, str):
            raise TypeError("text must be a str")
        text = text.strip()
        if not cls._PATTERN.fullmatch(text):
            raise ValueError(f"invalid integer string: {text!r}")
        return cls(int(text))

    def __add__(self, other):
        if isinstance(other, Integer):
            return Integer(self.__value + other.value)
        if isinstance(other, Complex):
            return Complex(self.__value + other.real, other.imag)
        if isinstance(other, Matrix):
            return NotImplemented  # let Matrix.__radd__ handle it
        raise TypeError(
            f"unsupported operand type for +: {type(other).__name__}")

    def __mul__(self, other):
        if isinstance(other, Integer):
            return Integer(self.__value * other.value)
        if isinstance(other, Complex):
            return Complex(self.__value * other.real,
                           self.__value * other.imag)
        if isinstance(other, Matrix):
            return NotImplemented  # let Matrix.__rmul__ handle it
        raise TypeError(
            f"unsupported operand type for *: {type(other).__name__}")

    def __neg__(self):
        return Integer(-self.__value)

    def __eq__(self, other):
        if isinstance(other, Integer):
            return self.__value == other.value
        if isinstance(other, Complex):
            return other.imag == 0 and other.real == self.__value
        return NotImplemented

    def __hash__(self):
        return hash((self.__value, 0))

    def __repr__(self):
        return f"Integer({self.__value})"

    def __str__(self):
        return str(self.__value)


class Complex(AlgebraicElement):
    _PATTERN = re.compile(r"([+-]?[0-9]+)([+-][0-9]+)i")

    def __init__(self, real: int, imag: int):
        if not _is_int(real) or not _is_int(imag):
            raise TypeError("Complex components must be ints")
        self.__real = real
        self.__imag = imag

    @property
    def real(self) -> int:
        return self.__real

    @property
    def imag(self) -> int:
        return self.__imag

    @classmethod
    def from_string(cls, text: str):
        if not isinstance(text, str):
            raise TypeError("text must be a str")
        match = cls._PATTERN.fullmatch(text.strip())
        if not match:
            raise ValueError(f"invalid complex string: {text!r}")
        return cls(int(match.group(1)), int(match.group(2)))

    def __add__(self, other):
        if isinstance(other, Integer):
            return Complex(self.__real + other.value, self.__imag)
        if isinstance(other, Complex):
            return Complex(self.__real + other.real, self.__imag + other.imag)
        if isinstance(other, Matrix):
            return NotImplemented
        raise TypeError(
            f"unsupported operand type for +: {type(other).__name__}")

    def __mul__(self, other):
        if isinstance(other, Integer):
            return Complex(self.__real * other.value,
                           self.__imag * other.value)
        if isinstance(other, Complex):
            a, b, c, d = self.__real, self.__imag, other.real, other.imag
            return Complex(a * c - b * d, a * d + b * c)
        if isinstance(other, Matrix):
            return NotImplemented
        raise TypeError(
            f"unsupported operand type for *: {type(other).__name__}")

    def __neg__(self):
        return Complex(-self.__real, -self.__imag)

    def __eq__(self, other):
        if isinstance(other, Integer):
            return self.__imag == 0 and self.__real == other.value
        if isinstance(other, Complex):
            return self.__real == other.real and self.__imag == other.imag
        return NotImplemented

    def __hash__(self):
        return hash((self.__real, self.__imag))

    def __repr__(self):
        return f"Complex({self.__real}, {self.__imag})"

    def __str__(self):
        sign = "-" if self.__imag < 0 else "+"
        return f"{self.__real}{sign}{abs(self.__imag)}i"


# --------------------------------------------------------------------------
# Part 2 & 3: Matrix
# --------------------------------------------------------------------------
class Matrix(AlgebraicElement):
    def __init__(self, rows: int, cols: int, elements: list):
        if not _is_int(rows) or not _is_int(cols):
            raise TypeError("rows and cols must be ints")
        if rows <= 0 or cols <= 0:
            raise ValueError("rows and cols must be positive")
        if not isinstance(elements, (list, tuple)):
            raise TypeError("elements must be a list")
        if len(elements) != rows * cols:
            raise ValueError("len(elements) must equal rows * cols")
        for e in elements:
            if not isinstance(e, (Integer, Complex)):
                raise TypeError("elements must be Integer or Complex")
        self.__rows = rows
        self.__cols = cols
        # Private immutable copy: later changes to the caller's list
        # cannot affect this matrix.
        self.__elements = tuple(elements)

    @property
    def rows(self) -> int:
        return self.__rows

    @property
    def cols(self) -> int:
        return self.__cols

    @property
    def elements(self) -> tuple:
        return self.__elements

    # ---- static methods ---------------------------------------------------
    @staticmethod
    def _check_matrix(matrix):
        if not isinstance(matrix, Matrix):
            raise TypeError("argument must be a Matrix")

    @staticmethod
    def make_unit_matrix(n):
        if not _is_int(n):
            raise TypeError("n must be an int")
        if n <= 0:
            raise ValueError("n must be positive")
        elems = [Integer(1 if i == j else 0)
                 for i in range(n) for j in range(n)]
        return Matrix(n, n, elems)

    @staticmethod
    def get_ith_row(matrix, i):
        Matrix._check_matrix(matrix)
        if not _is_int(i):
            raise TypeError("index must be an int")
        if not 0 <= i < matrix.rows:
            raise IndexError("row index out of range")
        start = i * matrix.cols
        return list(matrix.elements[start:start + matrix.cols])

    @staticmethod
    def get_ith_col(matrix, j):
        Matrix._check_matrix(matrix)
        if not _is_int(j):
            raise TypeError("index must be an int")
        if not 0 <= j < matrix.cols:
            raise IndexError("column index out of range")
        return list(matrix.elements[j::matrix.cols])

    @staticmethod
    def is_zero_matrix(matrix):
        Matrix._check_matrix(matrix)
        zero = Integer(0)
        return all(e == zero for e in matrix.elements)

    @staticmethod
    def is_unit_matrix(matrix):
        Matrix._check_matrix(matrix)
        if matrix.rows != matrix.cols:
            return False
        zero, one = Integer(0), Integer(1)
        for i in range(matrix.rows):
            for j in range(matrix.cols):
                e = matrix.elements[i * matrix.cols + j]
                if e != (one if i == j else zero):
                    return False
        return True

    @staticmethod
    def is_top_triangular_matrix(matrix):
        """Square, and every element below the main diagonal is zero."""
        Matrix._check_matrix(matrix)
        if matrix.rows != matrix.cols:
            return False
        zero = Integer(0)
        return all(matrix.elements[i * matrix.cols + j] == zero
                   for i in range(matrix.rows) for j in range(i))

    @staticmethod
    def is_bottom_triangular_matrix(matrix):
        """Square, and every element above the main diagonal is zero."""
        Matrix._check_matrix(matrix)
        if matrix.rows != matrix.cols:
            return False
        zero = Integer(0)
        return all(matrix.elements[i * matrix.cols + j] == zero
                   for i in range(matrix.rows)
                   for j in range(i + 1, matrix.cols))

    # ---- class method -----------------------------------------------------
    @classmethod
    def make_matrix_from_string(cls, elements: str):
        if not isinstance(elements, str):
            raise TypeError("elements must be a str")
        if not elements.strip():
            raise ValueError("empty matrix string")
        rows = []
        for row_text in elements.split(";"):
            tokens = row_text.split()
            if not tokens:
                raise ValueError("empty row in matrix string")
            rows.append([
                Complex.from_string(t) if t.endswith("i")
                else Integer.from_string(t)
                for t in tokens
            ])
        width = len(rows[0])
        if any(len(r) != width for r in rows):
            raise ValueError("rows have different lengths")
        flat = [e for r in rows for e in r]
        return cls(len(rows), width, flat)

    # ---- operators --------------------------------------------------------
    def __eq__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        return (self.rows == other.rows and self.cols == other.cols
                and all(a == b for a, b in zip(self.elements, other.elements)))

    def __hash__(self):
        return hash((self.rows, self.cols, self.elements))

    def __add__(self, other):
        if isinstance(other, Matrix):
            if (self.rows, self.cols) != (other.rows, other.cols):
                raise ValueError("matrix dimensions must match for addition")
            elems = [a + b for a, b in zip(self.elements, other.elements)]
            return Matrix(self.rows, self.cols, elems)
        if isinstance(other, (Integer, Complex)):
            return Matrix(self.rows, self.cols,
                          [e + other for e in self.elements])
        raise TypeError(
            f"unsupported operand type for +: {type(other).__name__}")

    def __radd__(self, other):
        # Reached for scalar + matrix (after Integer/Complex return
        # NotImplemented). Addition is commutative here.
        return self + other

    def __mul__(self, other):
        if isinstance(other, Matrix):
            if self.cols != other.rows:
                raise ValueError(
                    "inner dimensions must match for multiplication")
            elems = []
            for i in range(self.rows):
                row = Matrix.get_ith_row(self, i)
                for j in range(other.cols):
                    col = Matrix.get_ith_col(other, j)
                    total = row[0] * col[0]
                    for a, b in zip(row[1:], col[1:]):
                        total = total + a * b
                    elems.append(total)
            return Matrix(self.rows, other.cols, elems)
        if isinstance(other, (Integer, Complex)):
            return Matrix(self.rows, self.cols,
                          [e * other for e in self.elements])
        raise TypeError(
            f"unsupported operand type for *: {type(other).__name__}")

    def __rmul__(self, other):
        # scalar * matrix: scalars are commutative, so reuse __mul__.
        # (Matrix * Matrix never reaches here; Python calls __mul__ first.)
        return self * other

    def __neg__(self):
        return Matrix(self.rows, self.cols, [-e for e in self.elements])

    def __repr__(self):
        return (f"Matrix({self.rows}, {self.cols}, "
                f"{list(self.elements)!r})")

    def __str__(self):
        lines = []
        for i in range(self.rows):
            row = Matrix.get_ith_row(self, i)
            lines.append("[" + " ".join(str(e) for e in row) + "]")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Standalone function using duck typing
# --------------------------------------------------------------------------
def multiply(a, b):
    """Return a * b for any objects that support the * operator."""
    return a * b
