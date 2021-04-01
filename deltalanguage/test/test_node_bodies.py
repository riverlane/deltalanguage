import unittest
from unittest.mock import Mock
from typing import OrderedDict

from deltalanguage.wiring import (PyConstBody,
                                  PyFuncBody,
                                  PyMethodBody)


class MockCallback(Mock):

    @property
    def __name__(self):
        return "mock_callback"


class TestPyConstBody(unittest.TestCase):
    """Unit tests for PyConstBody."""

    def setUp(self):
        self.mock_callback = MockCallback()

    def test_callback(self):
        """Callback should be called."""
        node_body = PyConstBody(self.mock_callback)
        node_body.eval()
        self.mock_callback.assert_called()

    def test_return_value(self):
        """Evaluated value should be returned."""
        self.mock_callback.return_value = 3
        node_body = PyConstBody(self.mock_callback)
        self.assertEqual(3, node_body.eval())

    def test_evaluated_once(self):
        """Callback should be called only once, even if evaluated multiple
        times.
        """
        node_body = PyConstBody(self.mock_callback)
        node_body.eval()
        node_body.eval()
        self.mock_callback.assert_called_once()

    def test_args_eval(self):
        """Arguments should be evaluated and used."""
        mock_arg = MockCallback()
        mock_arg.body.eval.return_value = 5
        mock_arg.index = None
        mock_arg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, mock_arg)
        node_body.eval()
        mock_arg.body.eval.assert_called()
        self.mock_callback.assert_called_with(5)

    def test_args_evaluated_once(self):
        """Arguments should be evaluated and used only once."""
        mock_arg = MockCallback()
        mock_arg.body.eval.return_value = 5
        mock_arg.index = None
        mock_arg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, mock_arg)
        node_body.eval()
        node_body.eval()
        mock_arg.body.eval.assert_called_once()

    def test_forked_args(self):
        """If argument node gives forked return, only used indexed argument."""
        mock_arg = MockCallback()
        mock_arg.body.eval.return_value = 5, 6
        mock_arg.index = 'x'
        mock_arg.outputs = OrderedDict([('x', int), ('y', int)])
        node_body = PyConstBody(self.mock_callback, mock_arg)
        node_body.eval()
        self.mock_callback.assert_called_with(5)

    def test_kwargs_eval(self):
        """Keyword arguments should be evaluated and used."""
        mock_kwarg = MockCallback()
        mock_kwarg.body.eval.return_value = 5
        mock_kwarg.index = None
        mock_kwarg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, a=mock_kwarg)
        node_body.eval()
        mock_kwarg.body.eval.assert_called()
        self.mock_callback.assert_called_with(a=5)

    def test_kwargs_evaluated_once(self):
        """Keyword arguments should be evaluated and used only once."""
        mock_kwarg = MockCallback()
        mock_kwarg.body.eval.return_value = 5
        mock_kwarg.index = None
        mock_kwarg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, a=mock_kwarg)
        node_body.eval()
        node_body.eval()
        mock_kwarg.body.eval.assert_called_once()

    def test_forked_kwargs(self):
        """If keyword argument node gives forked return, only used indexed
        argument.
        """
        mock_kwarg = MockCallback()
        mock_kwarg.body.eval.return_value = 5, 6
        mock_kwarg.index = 'x'
        mock_kwarg.outputs = OrderedDict([('x', int), ('y', int)])
        node_body = PyConstBody(self.mock_callback, a=mock_kwarg)
        node_body.eval()
        self.mock_callback.assert_called_with(a=5)

    def test_globals(self):
        """Setting up globals in the environment."""
        a = 3

        def add_2():
            return a+2
        node_body = PyConstBody(add_2)
        self.assertEqual(5, node_body.eval())

    def test_receive_none_arg_nonoptional(self):
        """None should not be received for args."""
        mock_arg = MockCallback()
        mock_arg.body.eval.return_value = None
        mock_arg.index = None
        mock_arg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, mock_arg)
        with self.assertRaises(ValueError):
            node_body.eval()

    def test_receive_none_forked_arg_nonoptional(self):
        """None should not be received for args."""
        mock_arg = MockCallback()
        mock_arg.body.eval.return_value = None, 3
        mock_arg.index = 'x'
        mock_arg.outputs = OrderedDict([('x', int), ('y', int)])
        node_body = PyConstBody(self.mock_callback, mock_arg)
        with self.assertRaises(ValueError):
            node_body.eval()

    def test_receive_none_kwarg_nonoptional(self):
        """None should not be received for kwargs."""
        mock_kwarg = MockCallback()
        mock_kwarg.body.eval.return_value = None
        mock_kwarg.index = None
        mock_kwarg.outputs = OrderedDict([('x', int)])
        node_body = PyConstBody(self.mock_callback, a=mock_kwarg)
        with self.assertRaises(ValueError):
            node_body.eval()

    def test_receive_none_forked_kwarg_nonoptional(self):
        """None should not be received for kwargs."""
        mock_kwarg = MockCallback()
        mock_kwarg.body.eval.return_value = None, 3
        mock_kwarg.index = 'x'
        mock_kwarg.outputs = OrderedDict([('x', int), ('y', int)])
        node_body = PyConstBody(self.mock_callback, a=mock_kwarg)
        with self.assertRaises(ValueError):
            node_body.eval()


class TestPyFuncBody(unittest.TestCase):

    def test_callback(self):
        """Test function callback is called correctly."""
        mock_callback = MockCallback()
        node_body = PyFuncBody(mock_callback)
        node_body.eval(1, 2, 3, a=4, b=5)
        mock_callback.assert_called_with(1, 2, 3, a=4, b=5)

    def test_return(self):
        """Return value should be correct."""
        mock_callback = MockCallback()
        mock_callback.return_value = 6
        node_body = PyFuncBody(mock_callback)
        self.assertEqual(node_body.eval(1, 2, 3, a=4, b=5), 6)

    def test_globals(self):
        """Setting up global variables in environment."""
        a = 5

        def return_global():
            return a+1

        node_body = PyFuncBody(return_global)
        self.assertEqual(node_body.eval(), 6)


class TestPyMethodBody(unittest.TestCase):

    def test_method_callback(self):
        """Test method callback is called correctly."""
        mock_object = MockCallback()
        node_body = PyMethodBody(mock_object.mock_callback, mock_object)
        node_body.eval(1, 2, 3, a=4, b=5)
        mock_object.mock_callback.assert_called_with(
            mock_object, 1, 2, 3, a=4, b=5)

    def test_method_globals(self):
        """Adding globals."""

        a = 12

        class TestClass:
            def add_5(self):
                return a+5
        test_object = TestClass()
        node_body = PyMethodBody(
            TestClass.add_5, test_object)
        self.assertEqual(17, node_body.eval())


if __name__ == "__main__":
    unittest.main()
