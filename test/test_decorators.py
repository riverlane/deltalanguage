import unittest

from deltalanguage.wiring import DeltaBlock, DeltaMethodBlock


class DecoratorTest(unittest.TestCase):
    """Test that decorators raise errors without explicit I/O typing."""

    def test_no_arg_type(self):
        with self.assertRaises(TypeError):
            @DeltaBlock(name="add")
            def _add(a, b: int) -> int:
                return a + b

    def test_no_return_type(self):
        with self.assertRaises(TypeError):
            @DeltaBlock(name="add")
            def _add(a: int, b: int):
                return a + b

    def test_class_no_arg_type(self):
        with self.assertRaises(TypeError):
            class _AdderNoArgType:

                def __init__(self, x: int):
                    self._x = x

                @DeltaMethodBlock(name="add_x")
                def add_x(self, a) -> int:
                    return a + self._x

    def test_class_no_return_type(self):
        with self.assertRaises(TypeError):
            class _AdderNoReturnType:

                def __init__(self, x: int):
                    self._x = x

                @DeltaMethodBlock(name="add_x")
                def add_x(self, a: int):
                    return a + self._x


if __name__ == "__main__":
    unittest.main()
