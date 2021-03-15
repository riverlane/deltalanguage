from abc import ABC, abstractmethod
import logging
from typing import TYPE_CHECKING, Callable, List, Dict, Type, Optional, Union

from deltalanguage.data_types import BaseDeltaType, DOptional

from ._node_classes.latency import Latency
from ._node_classes.node_bodies import (PyFuncBody,
                                        PyInteractiveBody,
                                        PyMethodBody,
                                        PyConstBody)
if TYPE_CHECKING:
    from ._node_classes.real_nodes import PythonNode


class BodyTemplate(ABC):
    """Body templates are responsible for storing some of the data for node 
    construction, specifically the data for an individual constructor.
    The most important piece of info of this type is the body
    and how to create it. 

    While :py:class:`NodeTemplate` contains enough information to create a 
    body-less node, ``NodeTemplate`` with one or more ``BodyTemplates`` is able
    to create a node with bodies.

    Parameters
    ----------
    name : str
        Name specific to this constructor
    latency : Latency
        Latency for the body this BodyTemplate will construct
    tags : List[str]
        List of user defined tags for the body this BodyTemplate will construct
    lvl : int
        The level at which logs are displayed.
    """

    def __init__(self,
                 name: str,
                 latency: Latency,
                 lvl: int = logging.ERROR,
                 tags: List[str] = []):
        self.name = name
        self.latency = latency
        self.lvl = lvl
        self._tags = tags

        self.construction_ready = True
        self.allow_const = False

        self._node_template = None
        self._graph = None

    def set_node_template(self, node_template: 'NodeTemplate'):
        """A ``BodyTemplate`` needs to have a parent NodeTemplate so it can
        possibly be linked up to other ``BodyTemplates`` that construct similar
        bodies.

        Parameters
        ----------
        node_template : NodeTemplate
        """
        self._node_template = node_template

    @property
    def out_type(self) -> Type:
        return self._node_template.out_type

    @property
    def in_params(self) -> Dict[str, Type]:
        return self._node_template.in_params

    @property
    def in_port_size(self) -> int:
        return self._node_template.in_port_size

    @property
    def node_key(self) -> Optional[str]:
        return self._node_template.node_key

    def compatible(self,
                   node_key: Optional[str],
                   in_port_size: int,
                   in_params: Dict[str, Union[BaseDeltaType, DOptional]],
                   out_type: Union[BaseDeltaType, DOptional]) -> bool:
        """Checks compatibility between the ``NodeTemplate`` of this 
        ``BodyTemplate`` and some params that are important for node creation.

        Returns
        -------
        bool
            ``True`` if paramaters are compatible with this ``NodeTemplate``
        """
        return self._node_template.compatible(node_key, in_port_size,
                                              in_params, out_type)

    @abstractmethod
    def construct_body(self):
        """Construct the body that this ``BodyTemplate`` is a template for.
        """
        pass

    def construct_const_body(self):
        """If possible, create the constant version of the body this
        ``BodyTemplate`` is a template for, else raise ``AttributeError``.
        """
        raise AttributeError("Const body construction attempted on body "
                             "template that does not support const body")

    def _call(self, graph, *args, **kwargs):
        body = self.construct_body()
        return self._node_template._standardised_call(graph, self.name,
                                                      self.lvl, self, body,
                                                      *args, **kwargs)

    def call(self, *args, **kwargs):
        """Construct a node using this ``BodyTemplate`` and its associated 
        :py:class:`NodeTemplate`.

        Parameters
        ----------
        args
            Input nodes as a list.
        kwargs
            Input nodes specified by keyword.
        """
        from ._delta_graph import DeltaGraph
        if DeltaGraph.stack():
            graph = DeltaGraph.current_graph()
            return self._call(graph, *args, **kwargs)
        else:
            raise ValueError("Node templte called when no graph was active.")

    def call_with_graph(self, graph, *args, **kwargs):
        """Construct a node using this ``BodyTemplate`` and its associated 
        :py:class:`NodeTemplate` using a non-standard (not in the stack) graph.

        Parameters
        ----------
        graph : DeltaGraph
            The graph the new node will be attached to
        args
            Input nodes as a list.
        kwargs
            Input nodes specified by keyword.
        """
        return self._call(graph, *args, **kwargs)


class FuncBodyTemplate(BodyTemplate):
    """Body template for nodes with a :py:class:`PyFuncBody`

    Parameters
    ----------
    name : str
        Name specific to this constructor.
    latency : Latency
        Latency for the body this BodyTemplate will construct.
    fn : Callable
        Function for the bodies this template creates.
    allow_const : bool
        Is the body this template produces allowed to be created as a 
        constant body.
    tags : List[str]
        List of user defined tags for the body this BodyTemplate will
        construct.
    """

    def __init__(self,
                 name: str,
                 latency: Latency,
                 lvl: int,
                 fn: Callable,
                 allow_const: bool,
                 tags: List[str] = []):
        super().__init__(name, latency, lvl, tags)
        self._callback = fn
        self.allow_const = allow_const

    def construct_const_body(self, *pos_in_nodes, **kw_in_nodes):
        """If allowed, create the constant version :py:class:`PyConstBody` 
        version of this function body
        """
        if not self.allow_const:
            raise AttributeError("Const body construction attempted on sub-"
                                 "template that does not support const body")
        else:
            return PyConstBody(self._callback, *pos_in_nodes, **kw_in_nodes)

    def construct_body(self):
        """Construct the :py:class:`PyFuncBody` that this ``BodyTemplate`` is
        a template for
        """
        return PyFuncBody(self._callback, self.latency, self._tags)


class MethodBodyTemplate(FuncBodyTemplate):
    """Body template for nodes with a :py:class:`PyMethodBody`

    Parameters
    ----------
    name : str
        Name specific to this constructor.
    latency : Latency
        Latency for the body this BodyTemplate will construct.
    fn : Callable
        Function for the bodies this template creates.
    tags : List[str]
        List of user defined tags for the body this BodyTemplate will
        construct.
    """

    def __init__(self,
                 name: str,
                 latency: Latency,
                 lvl: int,
                 fn: Callable,
                 tags: List[str] = []):
        super().__init__(name, latency, lvl, fn, False, tags)
        self.construction_ready = False

    def construct_body(self, obj):
        """Construct the :py:class:`PyMethodBody` that this ``BodyTemplate``
        is a template for.
        """
        return PyMethodBody(self._callback, obj, self.latency, self._tags)

    def _call(self, graph, obj, *args, **kwargs):
        body = self.construct_body(obj)
        return self._node_template._standardised_call(graph, self.name,
                                                      self.lvl, self, body,
                                                      *args, **kwargs)


class InteractiveBodyTemplate(BodyTemplate):
    """Body template for nodes with a :py:class:`PyInteractiveBody`

    Parameters
    ----------
    name : str
        Name specific to this constructor
    latency : Latency
        Latency for the body this BodyTemplate will construct.
    proc : Callable[[PythonNode], None]
        Process for the bodies this template creates.
    tags : List[str]
        List of user defined tags for the body this BodyTemplate will
        construct.
    """

    def __init__(self,
                 name: str,
                 latency: Latency,
                 lvl: int,
                 proc: Callable[['PythonNode'], None],
                 tags: List[str] = []):
        super().__init__(name, latency, lvl, tags)
        self._proc = proc

    def construct_body(self):
        """Construct the :py:class:`PyInteractiveBody` that this 
        ``BodyTemplate`` is a template for.
        """
        return PyInteractiveBody(self._proc, self._tags)

    def _call(self, graph, *args, **kwargs):
        if args:
            raise ValueError("Please use keywords for interactive node "
                             "input specification.")
        body = self.construct_body()
        return self._node_template._standardised_call(graph, self.name,
                                                      self.lvl, self, body,
                                                      *args, **kwargs)
