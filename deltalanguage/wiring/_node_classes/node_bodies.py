"""Classes to represent different node bodies a Deltaflow node could represent.
"""
from abc import ABC, abstractmethod
from typing import Callable, List

import dill
import dis
import logging

from deltalanguage.logging import make_logger
from deltalanguage.data_types import DeltaIOError
from .latency import Latency


log = make_logger(logging.WARNING, "Bodies")


class Body(ABC):

    def __init__(self,
                 latency: Latency = Latency(time=300),
                 tags: List[str] = None):
        """
        Parameters
        ----------
        latency : Latency
            Estimated time this body takes to run
        tags : List[str]
            List of strings to be added as access tags.
        """
        tags = tags if tags is not None else []
        self._access_tags = tags + type(self).mro()
        self.latency = latency

    @property
    def access_tags(self) -> List[object]:
        """List of ways this body wants to identify itself.
        These are usually a list of classes and a list of user added strings.

        Returns
        -------
        List[object]
            A list of immutable objects to be used as keys in a dict
        """
        return self._access_tags

    @property
    @abstractmethod
    def language(self) -> str:
        """String representation of the language represented by this body class.

        Returns
        -------
        str
        """
        pass

    @property
    @abstractmethod
    def as_serialized(self) -> str:
        """Serialisation of body as string.

        Returns
        -------
        str
        """
        pass

    def __eq__(self, other) -> bool:
        if not isinstance(other, Body):
            return False

        if self._access_tags != other._access_tags:
            return False

        if self.latency != other.latency:
            return False

        return True


class PythonBody(Body):

    def python_body_eq(self, other, my_callback):

        # Body class must be the same
        if type(self) != type(other):
            print(type(self))
            print(type(other))
            return False

        if my_callback.__name__ != other.callback.__name__:
            return False

        if my_callback.__code__.co_varnames != other.callback.__code__.co_varnames:
            return False

        if my_callback.__code__.co_consts != other.callback.__code__.co_consts:
            return False

        my_instructions = list(dis.get_instructions(my_callback))
        other_instructions = list(dis.get_instructions(other.callback))
        if len(my_instructions) != len(other_instructions):
            return False

        for (i, j) in zip(my_instructions, other_instructions):
            if (i.opcode, i.arg, i.argval) != (j.opcode, j.arg, j.argval):
                return False

        return True

    @staticmethod
    def freevar_check(my_callback, other_callback):
        if my_callback.__code__.co_freevars != other_callback.__code__.co_freevars:
            return False
        else:
            if (my_callback.__code__.co_freevars and
                    my_callback.__code__.co_freevars != ('self',)):
                log.warning("Equality called on bodies where functions have free "
                            f"variables: {my_callback.__code__.co_freevars}")
        return True

    @property
    def language(self) -> str:
        """Language of the body.

        Returns
        -------
        str
        """
        return "Py"

    @property
    def as_serialized(self) -> str:
        """Serialisation of body as string.

        Returns
        -------
        str
        """
        return dill.dumps(self, recurse=True)


class PyFuncBody(PythonBody):
    """Node body for python functions.

    Parameters
    ----------
    fn : Callable
        A callable object that will play a role of the body.
    environment : Callable
        Link to the environment.
    """

    def __init__(self, fn: Callable,
                 latency: Latency = Latency(time=350),
                 tags: List[str] = None):
        tags = tags if tags is not None else []
        super().__init__(latency, tags + [fn.__name__])
        self.callback = fn

    def eval(self, *args, **kwargs):
        return self.callback(*args, **kwargs)

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism as component of .df file.
        """
        if not self.python_body_eq(other, self.callback):
            return False

        if not self.freevar_check(self.callback, other.callback):
            return False

        return super().__eq__(other)


class PyConstBody(PythonBody):
    """Node body for python are to be treated as constant.

    This means when its value is first queried it evaluates and from then on
    always returns this value.

    Parameters
    ----------
    fn : Callable
        A callable object that will play a role of the body.
    environment : Callable
        Link to the environment.
    value
        For a pure constant node that just represents a single constant value,
        a single value can be given. The given ``fn`` should return this value.
    args
        Constant arguments for the body.
    kwargs
        Constant keyworded arguments for the body.
    """

    def __init__(self, fn, *args,
                 value=None,
                 latency: Latency = Latency(time=100),
                 tags: List[str] = None, **kwargs):
        tags = tags if tags is not None else []
        super().__init__(latency, tags + [fn.__name__])
        self.constant_value = value
        self.callback = fn

        if self.constant_value is not None:
            if self.callback() != value:
                raise DeltaIOError("Callback on pure const node not equal to "
                                   f"provided value {value}.")

        self.args = args
        self.kwargs = kwargs

    def eval(self):
        if self.constant_value is None:
            # Evaluate value the first time the node is evaluated
            evaluated_args = []
            for arg in self.args:
                possible_arg = getattr(arg, "body", None)
                if possible_arg is not None:
                    evaluated_arg = possible_arg.eval()
                    # If previous node has multi output
                    # only get the relevant argument
                    if len(arg.outputs) > 1:
                        i = list(arg.outputs.keys()).index(arg.index)
                        evaluated_arg = evaluated_arg[i]
                    if evaluated_arg is not None:
                        evaluated_args.append(evaluated_arg)
                    else:
                        raise ValueError("Node with a constant body cannot "
                                         "receive \'None\' as input.")

            evaluated_kwargs = {}
            for key, arg in self.kwargs.items():
                possible_kwarg = getattr(arg, "body", None)
                if possible_kwarg is not None:
                    evaluated_kwarg = possible_kwarg.eval()
                    # If previous node has multi output
                    # only get the relevant keyword argument
                    if len(arg.outputs) > 1:
                        i = list(arg.outputs.keys()).index(arg.index)
                        evaluated_kwarg = evaluated_kwarg[i]
                    if evaluated_kwarg is not None:
                        evaluated_kwargs[key] = evaluated_kwarg
                    else:
                        raise ValueError("Node with a constant body cannot "
                                         "receive \'None\' as input.")

            self.constant_value = self.callback(
                *evaluated_args, **evaluated_kwargs)

        return self.constant_value

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism as component of .df file.
        """
        if not self.python_body_eq(other, self.callback):
            return False

        if self.constant_value != other.constant_value:
            return False

        if (self.constant_value is not None and
                not self.freevar_check(self.callback, other.callback)):
            return False

        # args and kwargs are not tested for equality due to recursion.
        # They are however implictly checked when testing graph
        # connectivity in graph equality checks.
        # Here, we just check there are the same number of arguments
        if len(self.args) + len(self.kwargs) != len(other.args) + len(other.kwargs):
            return False

        return super().__eq__(other)


class PyMethodBody(PythonBody):
    """Node body for python methods.

    Must store instance to run with when instantiated. Uses this instance when
    evaluated.

    Parameters
    ----------
    fn : Callable
        A callable object that will play a role of the body.
    instance : object
        Object instance for state storage.
    environment : Callable
        Link to the environment.
    """

    def __init__(self, fn, instance,
                 latency: Latency = Latency(time=350),
                 tags: List[str] = None):
        tags = tags if tags is not None else []
        super().__init__(latency, tags + [fn.__name__])
        self.callback = fn
        self.instance = instance

    def eval(self, *args, **kwargs):
        return self.callback(self.instance, *args, **kwargs)

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism as component of .df file.
        """
        if not self.python_body_eq(other, self.callback):
            return False

        if not self.freevar_check(self.callback, other.callback):
            return False

        # Instances need not be the same, but their type is expected to be
        if type(self.instance).__name__ != type(other.instance).__name__:
            return False

        return super().__eq__(other)


class PyMigenBody(PyMethodBody):
    """Node body for migen methods.

    ..
        It's basically :py:class:`PyMethodBody`, but...
        the node is evaluated multiple times until we have an output.

        The reason for this is the following:

        - the result of the node is ready only after several cycles
        - in the meantime the result should be set to _some_ value, like
          ``None`` or ``(None, None, ...)``
        - I chose to set the entire output to None until the node produces
        a result

        This policy should be revised when we start working on protocol
        adaptors.

        :py:meth:`MigenNodeTemplate.tb_generator` has the number of iterations
        defined, that number should be chosen such that it's enough to produce
        an output. Otherwise this body will loop forever.
    """

    def __init__(self, fn, instance,
                 latency: Latency = Latency(clocks=1),
                 tags: List[str] = None):
        super().__init__(fn, instance, latency, tags)

    def eval(self, *args, **kwargs):
        """Overwrites :meth:`PyMethodBody.eval`."""
        while True:
            ret = self.callback(self.instance, *args, **kwargs)
            if ret is not None:
                if len(ret) == 1:
                    ret = ret[0]
                return ret

    @property
    def as_serialized(self) -> str:
        """Serialisation of body as string.

        Returns
        -------
        str
        """
        return str(self.instance.get_serialised_body())


class PyInteractiveBody(PyFuncBody):
    """Body class to represent bodies that expose queues to the designer.
    We explicitily define this class to enable custom-code creation in the
    runtimes.
    """
