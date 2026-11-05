import io
import os
import unittest
from contextlib import redirect_stdout

import main

HERE = os.path.join(os.path.dirname(__file__), "samples")


class TestQueraSamples(unittest.TestCase):
    def run_sample(self, name):
        with open(os.path.join(HERE, name + ".in")) as f:
            buf = io.StringIO()
            with redirect_stdout(buf):
                main.main(f)
        with open(os.path.join(HERE, name + ".out")) as f:
            expected = f.read()
        self.assertEqual(buf.getvalue().splitlines(), expected.splitlines())

    def test_sample_1(self):
        self.run_sample("s1")

    def test_sample_2(self):
        self.run_sample("s2")


if __name__ == "__main__":
    unittest.main()
