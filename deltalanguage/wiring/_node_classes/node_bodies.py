"""Classes to represent different node bodies a Deltaflow node could represent.
"""
from abc import ABC, abstractmethod
from copy import copy
import dill
from typing import Any, Callable, List

from .latency import Latency

class Body(ABC):

    def __init__(self, latency: Latency = Latency(time=300), extra_tags: List[str] = []):
        """
        Parameters
        ----------
        latency : Latency
            esimated time this body takes to run
        extra_tags : List[str]
            list of strings the user wants to add as extra access tags, 
            by default []
        """
        self._access_tags = extra_tags + type(self).mro()
        self.latency = latency

    @property
    def access_tags(self) -> List[object]:
        """List of ways this body wants to identify itself
        These are usually a list of classes and a list of user added strings

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
    def as_serialised(self) -> str:
        """Serialisation of body as string.

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

    @property
    def as_serialised(self) -> str:
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
                 extra_tags: List[str] = []):
        super().__init__(latency, extra_tags)
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

    def __init__(self, fn, *args,
                 latency: Latency = Latency(time=100),
                 extra_tags: List[str] = [], **kwargs):
        super().__init__(latency, extra_tags)
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

    def __init__(self, fn, instance,
                 latency: Latency = Latency(time=350),
                 extra_tags: List[str] = []):
        super().__init__(latency, extra_tags)
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

    def __init__(self, fn, instance,
                 latency: Latency = Latency(clocks=1),
                 extra_tags: List[str] = []):
        super().__init__(fn, instance, latency, extra_tags)

    def eval(self, *args, **kwargs):
        """Overwrites :meth:`PyMethodBody.eval`."""
        while True:
            ret = self.callback(self.instance, *args, **kwargs)
            if ret is not None:
                return ret

    @property
    def as_serialised(self) -> str:
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


class TemplateBody(PythonBody):
    """Body class to represent a body that is yet to be specified, but that
    has a pre-defined interface.

    The main pourpose of this type of node is that its body can be defined
    at a later stage of the Deltaflow programming, also known as running stage,
    as opposed to the programming stage where the graph is defined.

    Use :py:class:`template_node_factory` for construction in the
    context of :py:class:`DeltaGraph`.

    Parameters
    ----------
    kw_in_nodes : Dict[str, AbstractNode]
        The input nodes to this template node, specified by kwargs
    """

    def __init__(self, kw_in_nodes, extra_tags: List[str] = []):
        super().__init__(extra_tags)
        self.kw_in_nodes = kw_in_nodes
        self.inner_body = None

    def specify_by_func(
        self,
        my_func: Callable,
        allow_const: bool = True,
    ):

        if allow_const:
            self.inner_body = PyConstBody(my_func, **self.kw_in_nodes)
        else:
            self.inner_body = PyFuncBody(my_func)

    def eval(self, *args, **kwargs):

        if self.inner_body is None:
            raise ValueError("TemplateBody function is not defined!")
        return self.inner_body.eval(*args, **kwargs)
