import unittest
from unittest.mock import Mock
from typing import OrderedDict

from deltalanguage.wiring._node_classes.node_bodies import PythonBody
from deltalanguage.wiring import (Latency,
                                  PyConstBody,
                                  PyFuncBody,
                                  PyMethodBody)


class MockCallback(Mock):

    @property
    def __name__(self):
        return "mock_callback"


class TestBody(unittest.TestCase):
    """Tests for the abstract Body class. Tests are of behaviour that is common
    accross all body classes, but will use PyFuncBody in particular as Body is
    abstract and cannot be instantiated.
    """

    def test_eq(self):
        b1 = PythonBody(Latency(time=150), tags=['test_tag'])
        b2 = PythonBody(Latency(time=150), tags=['test_tag'])
        self.assertEqual(b1, b2)

    def test_neq_instance_diff(self):
        b1 = PythonBody(Latency(time=150), tags=['test_tag'])
        b2 = object()
        self.assertNotEqual(b1, b2)

    def test_neq_tags_diff(self):
        b1 = PythonBody(Latency(time=150), tags=['test_tag'])
        b2 = PythonBody(Latency(time=150))
        self.assertNotEqual(b1, b2)

        b3 = PythonBody(Latency(time=150), tags=['test_tag', 'test_tag_2'])
        self.assertNotEqual(b1, b3)

    def test_neq_latency_diff(self):
        b1 = PythonBody(Latency(time=151), tags=['test_tag'])
        b2 = PythonBody(Latency(time=150), tags=['test_tag'])
        self.assertNotEqual(b1, b2)


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

    def make_b3(self, *args, **kwargs):
        def b_callback(a, b):
            return a + b

        return PyConstBody(b_callback, value=None, *args, **kwargs)

    def make_b4(self, *args, **kwargs):
        def b_callback(a, b):
            return a + b + 0

        return PyConstBody(b_callback, value=None, *args, **kwargs)

    def test_eq_with_args(self):
        const_value = 1
        b1_1 = PyConstBody(lambda: const_value, value=const_value)
        b2_1 = PyConstBody(lambda: const_value, value=const_value)
        b3_1 = self.make_b3(b1_1, b2_1)

        b1_2 = PyConstBody(lambda: const_value, value=const_value)
        b2_2 = PyConstBody(lambda: const_value, value=const_value)
        b3_2 = self.make_b3(b1_2, b2_2)

        self.assertEqual(b3_1, b3_2)

    def test_eq_with_kwargs(self):
        const_value = 1
        b1_1 = PyConstBody(lambda: const_value, value=const_value)
        b2_1 = PyConstBody(lambda: const_value, value=const_value)
        b3_1 = self.make_b3(a=b1_1, b=b2_1)

        b1_2 = PyConstBody(lambda: const_value, value=const_value)
        b2_2 = PyConstBody(lambda: const_value, value=const_value)
        b3_2 = self.make_b3(a=b1_2, b=b2_2)

        self.assertEqual(b3_1, b3_2)

    def test_eq_with_args_and_kwargs(self):
        const_value = 1
        b1_1 = PyConstBody(lambda: const_value, value=const_value)
        b2_1 = PyConstBody(lambda: const_value, value=const_value)
        b3_1 = self.make_b3(b1_1, b2_1)

        b1_2 = PyConstBody(lambda: const_value, value=const_value)
        b2_2 = PyConstBody(lambda: const_value, value=const_value)
        b3_2 = self.make_b3(a=b1_2, b=b2_2)

        self.assertEqual(b3_1, b3_2)

    def test_eq_const_value(self):
        const_value = 7
        b1 = PyConstBody(lambda: const_value, value=const_value)
        b2 = PyConstBody(lambda: const_value, value=const_value)
        self.assertEqual(b1, b2)

    def test_neq_const_value_diff(self):
        const_value = 7
        const_value_2 = 8
        b1 = PyConstBody(lambda: const_value, value=const_value)
        b2 = PyConstBody(lambda: const_value_2, value=const_value_2)
        self.assertNotEqual(b1, b2)

    def test_neq_func_body_diff(self):
        const_value = 1
        b1_1 = PyConstBody(lambda: const_value, value=const_value)
        b2_1 = PyConstBody(lambda: const_value, value=const_value)
        b3 = self.make_b3(b1_1, b2_1)

        b1_2 = PyConstBody(lambda: const_value, value=const_value)
        b2_2 = PyConstBody(lambda: const_value, value=const_value)
        b4 = self.make_b4(b1_2, b2_2)

        self.assertNotEqual(b3, b4)


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

    def make_b1(self):
        def b_callback(a, b):
            return a + b

        return PyFuncBody(b_callback)

    def make_b2(self):
        def b_callback(a, b):
            return a + b

        return PyFuncBody(b_callback)

    def make_b3(self):
        def b_callback(a, b):
            return a + b + 0

        return PyFuncBody(b_callback)

    def make_b4(self):
        def b4_callback(a, b):
            return a + b

        return PyFuncBody(b4_callback)

    def make_b5(self):
        local_var = 1

        def b_callback(a, b):
            return a + b + local_var

        return PyFuncBody(b_callback)

    def make_b6(self):
        local_var = 2

        def b_callback(a, b):
            return a + b + local_var

        return PyFuncBody(b_callback)

    def test_eq(self):
        b1_1 = self.make_b1()
        b1_2 = self.make_b1()
        self.assertEqual(b1_1, b1_2)

        b2 = self.make_b2()
        self.assertEqual(b1_1, b2)

    def test_neq_func_code_diff(self):
        b1 = self.make_b1()
        b3 = self.make_b3()

        self.assertNotEqual(b1, b3)

    def test_neq_func_name_diff(self):
        b1 = self.make_b1()
        b4 = self.make_b4()

        self.assertNotEqual(b1, b4)

    def test_neq_func_local_diff(self):
        """Behavioral demonstration test.
        b5 and b6 are not actually equal. They will return different
        values for different inputs. But we currently have no way to
        tell that these two are not equal because their difference in
        behavior is hidden behind a free variable. So what we do is
        say return they are equal and also log a warning that there were
        free variables involved in a comparison between bodies.
        """
        b5 = self.make_b5()
        b6 = self.make_b6()

        self.assertEqual(b5, b6)


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

    def make_b1(self):
        class BodyInstance:
            def b_callback(self, a, b):
                return a + b

        instance = BodyInstance()
        return PyMethodBody(instance.b_callback, instance)

    def make_b2(self):
        class BodyInstance:
            def b_callback(self, a, b):
                return a + b

        instance = BodyInstance()
        return PyMethodBody(instance.b_callback, instance)

    def make_b3(self):
        class BodyInstance:
            def b_callback(self, a, b):
                return a + b + 0

        instance = BodyInstance()
        return PyMethodBody(instance.b_callback, instance)

    def make_b4(self):
        class BodyInstance4:
            def b_callback(self, a, b):
                return a + b

        instance = BodyInstance4()
        return PyMethodBody(instance.b_callback, instance)

    def test_eq(self):
        b1_1 = self.make_b1()
        b1_2 = self.make_b1()
        self.assertEqual(b1_1, b1_2)

        b2 = self.make_b2()
        self.assertEqual(b1_1, b2)

    def test_neq_func_body_diff(self):
        b1 = self.make_b1()
        b3 = self.make_b3()

        self.assertNotEqual(b1, b3)

    def test_neq_instance_class_name_diff(self):
        b1 = self.make_b1()
        b4 = self.make_b4()

        self.assertNotEqual(b1, b4)


if __name__ == "__main__":
    unittest.main()
