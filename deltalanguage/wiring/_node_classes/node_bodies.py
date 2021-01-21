"""Classes to represent different node bodies a Deltaflow node could represent.
"""
from abc import ABC, abstractmethod
from copy import copy
from typing import Any, Callable, NamedTuple


class Body(ABC):

    @property
    @abstractmethod
    def language(self) -> str:
        """String representation of the language represented by this body class.

        Returns
        -------
        str
        """
        pass


class PythonBody(Body):

    @property
    def language(self) -> str:
        """Language of the body.

        Returns
        -------
        str
        """
        return "Py"


class PyFuncBody(PythonBody):
    """Node body for python functions.

    Parameters
    ----------
    fn : Callable
        A callable object that will play a role of the body.
    environment : Callable
        Link to the environment.
    """

    def __init__(self, fn: Callable):
        self.callback = fn

    def eval(self, *args, **kwargs):
        return self.callback(*args, **kwargs)


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
    args
        Constant arguments for the body.
    kwargs
        Constant keyworded arguments for the body.
    """

    def __init__(self, fn, *args, **kwargs):
        self.value = None
        self.callback = fn
        self.args = args
        self.kwargs = kwargs

    def eval(self):
        if self.value is None:
            # Evaluate value the first time the node is evaluated
            evaluated_args = []
            for arg in self.args:
                possible_arg = getattr(arg, "body", None)
                if possible_arg is not None:
                    evaluated_arg = possible_arg.eval()
                    # If previous node has forked output
                    # only get the relevant argument
                    possible_index = getattr(arg, "index", None)
                    if possible_index is not None:
                        evaluated_arg = getattr(
                            evaluated_arg, possible_index, None)
                    if evaluated_arg is not None:
                        evaluated_args.append(evaluated_arg)
                    else:
                        raise ValueError("ConstNode received None")

            evaluated_kwargs = {}
            for key, arg in self.kwargs.items():
                possible_kwarg = getattr(arg, "body", None)
                if possible_kwarg is not None:
                    evaluated_kwarg = possible_kwarg.eval()
                    # If previous node has forked output
                    # only get the relevant keyword argument
                    possible_index = getattr(arg, "index", None)
                    if possible_index is not None:
                        evaluated_kwarg = getattr(
                            evaluated_kwarg, possible_index, None)
                    if evaluated_kwarg is not None:
                        evaluated_kwargs[key] = evaluated_kwarg
                    else:
                        raise ValueError("ConstNode received None")

            self.value = self.callback(*evaluated_args, **evaluated_kwargs)

        return self.value


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

    def __init__(self, fn, instance):
        self.callback = fn
        self.instance = instance

    def eval(self, *args, **kwargs):
        return self.callback(self.instance, *args, **kwargs)


class PyMigenBody(PyMethodBody):
    """Node body for migen methods.

    ..

        It's basically :py:class:`PyMethodBody`, but...
        the node is evaluated multiple times until we have an output.

        The reason for this is the following:

        - if a migen node has multiple outputs, they will be forked using
        ``make_forked_return``
        - the result of the node is ready only after several cycles
        - in the meantime the result should be set to _some_ value, like
          ``None`` or ``ForkedReturn(None, None, ...)``
        - I chose to set the entire output to None until the node produces
        a result

        This policy should be revised when we start working on protocol
        adaptors.

        :py:meth:`MigenNodeTemplate.tb_generator` has the number of iterations
        defined, that number should be chosen such that it's enough to produce
        an output. Otherwise this body will loop forever.
    """

    def eval(self, *args, **kwargs):
        """Overwrites :meth:`PyMethodBody.eval`."""
        while True:
            ret = self.callback(self.instance, *args, **kwargs)
            if ret is not None:
                return ret


class SplitterBody(Body):
    """Body class to represent bodies that duplicate a given input and return
    it to multiple output ports.

    Parameters
    ----------
    repeat_num : int
        Number of repetitions.

    .. deprecated:: 0.5
        Use ``DeltaGraph.do_automatic_splitting``.
    """

    def __init__(self, repeat_num: int):
        self.repeat_num = repeat_num


class PySplitterBody(SplitterBody, PythonBody):
    """Body class to represent bodies that duplicate a given input and return
    it to multiple output ports in Python.

    Parameters
    ----------
    repeat_num : int
        Number of repetitions.
    return_tuple : NamedTuple
        Constructor for return forking.

    .. deprecated:: 0.5
        Use ``DeltaGraph.do_automatic_splitting``.
    """

    def __init__(self, repeat_num: int, return_tuple: NamedTuple):
        super().__init__(repeat_num)
        self.return_tuple = return_tuple

    def eval(self, to_copy: Any):
        ret_vals = [copy(to_copy) for _ in range(0, self.repeat_num)]
        return self.return_tuple._make(ret_vals)


class PyInteractiveBody(PyFuncBody):
    """Body class to represent bodies that expose queues to the designer.
    We explicitily define this class to enable custom-code creation in the
    runtimes.
    """


class PyTupleOneCast(PythonBody):
    """Body class to encapsulate another body and cast the result to a tuple
    of one.
    """

    def __init__(self, inner_body: PythonBody):
        self.inner_body = inner_body

    def eval(self, *inner_args, **inner_kwargs):
        inner_val = self.inner_body.eval(*inner_args, **inner_kwargs)
        return tuple([inner_val])


class PyListOneCast(PythonBody):
    """Body class to encapsulate another body and cast the result to a list
    of one.
    """

    def __init__(self, inner_body: PythonBody):
        self.inner_body = inner_body

    def eval(self, *inner_args, **inner_kwargs):
        inner_val = self.inner_body.eval(*inner_args, **inner_kwargs)
        return [inner_val]


class Latency:
    """Latency of a graph node.

    Parameters
    ----------
    clocks : int
        The expected latency of the node in clock cycles.
    time : int
        The expected latency in real time.
    variance : int
        Variance of the node's latency.

    ..
        This is not used currently. Use cases:

        - latencies can be used by runtime to optimise the emulation process
        - latencies can be used for cost estimation of the algorithm; this
          requires latency estimation of inter-node connections as well.
    """

    def __init__(self, clocks: int = None, time: int = None, variance=0):
        # either a fixed number of clocks or a time, +- variance
        if clocks and time:
            raise ValueError(
                "cannot specify both a clock and time based latency"
            )
        self._clocks = clocks
        self._time = time  # as ns
        self.variance = variance

    def __str__(self) -> str:
        if self._clocks is not None:
            return f"c{self._clocks}"

        if self._time is not None:
            return f"t{self._time}"

        return "t0"
