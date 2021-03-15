import logging
from typing import TYPE_CHECKING, Callable, Dict, Union, Optional, Type

from deltalanguage.data_types import (as_delta_type,
                                      BaseDeltaType,
                                      DeltaIOError,
                                      DOptional,
                                      Void)
from deltalanguage.logging import make_logger
from ._node_classes.latency import Latency
from ._node_classes.node_bodies import Body
from ._node_classes.real_nodes import (PythonNode,
                                       as_node,
                                       get_func_in_params_out_type,
                                       in_params_as_delta_types)
from ._body_templates import (BodyTemplate,
                              FuncBodyTemplate,
                              InteractiveBodyTemplate,
                              MethodBodyTemplate)

if TYPE_CHECKING:
    from ._delta_graph import DeltaGraph

log = make_logger(logging.WARNING, "Node Templates")


class NodeTemplate():
    """NodeTemplates are recipes for how to create a specific node.
    They have a list of :py:class:`BodyTemplate`s that represent how to
    construct a number of different bodies for the node. Each
    ``BodyTemplate`` has a call method to allow creation of the
    node. This node will be given bodies from all valid ``BodyTemplates``.

    Parameters
    ----------
    name : str
        Default name for the nodes created using this node template
    in_params : Dict[str, Union[BaseDeltaType, DOptional]]
        List of input parameters for nodes created using this template
    out_type : Type
        Out type for nodes created using this template
    node_key : Optional[str]
        Node key to allow node object to be accessed inside bodies
        created using this template
    in_port_size : int
        Bounded size of port queues into this node
    """

    def __init__(self,
                 in_params: Dict[str, Type],
                 out_type: Type = Void,
                 name: str = None,
                 lvl: int = logging.ERROR,
                 node_key: Optional[str] = None,
                 in_port_size: int = 0):
        self.name = "template_" + name if name else "template"
        self.lvl = lvl
        self.node_key = node_key
        self.in_port_size = in_port_size

        self._body_templates = []

        self.in_params = in_params_as_delta_types(in_params)
        self.out_type = as_delta_type(out_type)

        self._has_optional_inputs = False
        for in_type in in_params.values():
            if isinstance(in_type, DOptional):
                self._has_optional_inputs = True

    def _standardised_call(self, graph, name: str, lvl: int,
                           caller: Optional[BodyTemplate] = None,
                           body: Optional[Body] = None,
                           *nodes, **kwnodes):
        """Internal method used by different node creation methods
        Contains several common behaviors for node creation

        Parameters
        ----------
        caller : BodyTemplate
            The BodyTemplate that initiated this node creation
        graph : DeltaGraph
            The graph this node will be attached to
        body : Body
            The body the caller BodyTemplate has provided for node creation
            This body is special as it always goes first in the body list.
        name : str
            Name of the node to create
        """
        # Input node sanitisation
        pos_in_nodes = [as_node(arg, graph) for arg in nodes]
        kw_in_nodes = {param_name: as_node(arg, graph)
                       for (param_name, arg) in kwnodes.items()}

        # Const folding logic
        all_args = pos_in_nodes + list(kw_in_nodes.values())
        num_const = sum([node.is_const() for node in all_args])
        all_allow_const = all(st.allow_const for st in self._body_templates)

        # Condition for node to be created as constant (all const bodies)
        const_condition_met = False
        if (all_allow_const
            and num_const == len(pos_in_nodes) + len(kw_in_nodes)
            and self.node_key is None
                and not self._has_optional_inputs):
            const_condition_met = True

        # Creation of bodies for all BodyTemplates
        if caller and const_condition_met:
            body = caller.construct_const_body(*pos_in_nodes, **kw_in_nodes)

        bodies = []
        if body is not None:
            bodies.append(body)

        for body_template in self._body_templates:
            if (body_template.construction_ready
                    and body_template is not caller):
                if const_condition_met:
                    bodies.append(body_template.construct_const_body(
                        *pos_in_nodes,
                        **kw_in_nodes))
                else:
                    bodies.append(body_template.construct_body())

        # Node creation and return
        ret_node = PythonNode(graph,
                              bodies,
                              self.in_params,
                              pos_in_nodes,
                              kw_in_nodes,
                              out_type=self.out_type,
                              name=name,
                              in_port_size=self.in_port_size,
                              node_key=self.node_key,
                              lvl=lvl)
        log.debug(f"making {type(ret_node)}: {ret_node.name}")
        return ret_node

    def merge(self, other: 'NodeTemplate'):
        """Check compatibility of two ``NodeTemplates`` and then merge the 
        one given as a parameter into this one.

        Parameters
        ----------
        other : NodeTemplate
            Other ``NodeTemplate`` to try to merge into this one.
        """
        if other is not self:
            if other.compatible(self.node_key, self.in_port_size,
                                self.in_params, self.out_type):
                for other_body_t in other._body_templates:
                    other_body_t.set_node_template(self)
                    self._body_templates.append(other_body_t)

    def add_constructor(self, body_template: Union[object, BodyTemplate]):
        """Add a body constructor to this ``NodeTemplate`` via a 
        ``BodyTemplate``.

        .. note::
          Main usage of this function is for when you have some body that can
          belong on your node constructor but the definition of that body is
          in some non-accessible code.

        Parameters
        ----------
        body_template : Union[object, BodyTemplate]
            ``BodyTemplate`` to merge or some object for which
            ``template`` is defined, where ``template`` is a ``BodyTemplate``
        """
        if not isinstance(body_template, BodyTemplate):
            body_template = body_template.template

        if body_template in self._body_templates:
            log.warning(f"Body template {body_template.name} attempted to join"
                        f" node template {self.name} more than one time")
        else:
            if body_template.compatible(self.node_key, self.in_port_size,
                                        self.in_params, self.out_type):
                self._body_templates.append(body_template)
                body_template.set_node_template(self)

    @staticmethod
    def _standardised_merge(
        other: Optional['NodeTemplate'],
        body_template: BodyTemplate,
        node_key: Optional[str],
        in_port_size: int,
        in_params: Dict[str, Union[BaseDeltaType, DOptional]],
        out_type: Union[BaseDeltaType, DOptional]
    ) -> BodyTemplate:
        """Internal method used by template merging and creation methods
        Contains the common behaviour for checking other_template is compatible
        with the given information. Also the common behaviour of creating a new
        NodeTemplate when there is no other_template.

        Parameters
        ----------
        other : Optional[NodeTemplate]
            The template that this method will add the body_template to after
            checks. May be None in which case new NodeTemplate created.
        body_template : BodyTemplate
            The BodyTemplate looking to be given a NodeTemplate to merge into.

        Returns
        -------
        BodyTemplate
            Returns the given BodyTemplate with its parent NodeTemplate
            attached. This parent NodeTemplate is either ``other_template`` or
            a newly created NodeTemplate.
        """
        if other and other.compatible(node_key, in_port_size,
                                      in_params, out_type):
            main_template = other
        else:
            main_template = NodeTemplate(in_params, out_type,
                                         name=body_template.name,
                                         node_key=node_key,
                                         in_port_size=in_port_size)
        body_template.set_node_template(main_template)
        main_template._body_templates.append(body_template)
        return body_template

    def compatible(self,
                   node_key: Optional[str],
                   in_port_size: int,
                   in_params: Dict[str, Union[BaseDeltaType, DOptional]],
                   out_type: Union[BaseDeltaType, DOptional]) -> bool:
        """Checks compatibility between this ``NodeTemplate`` and some params
        that are important for node creation.

        Returns
        -------
        bool
            ``True`` if paramaters are compatible with this ``NodeTemplate``.
        """
        if self.in_params != in_params:
            raise ValueError(f"Node template {self.name} "
                             "incompatible with given input parameters.")
        if self.out_type != out_type:
            raise ValueError(f"Node template {self.name} "
                             "incompatible with given out type.")
        if self.node_key != node_key:
            raise ValueError(f"Node template {self.name} "
                             "incompatible with given node type.")
        if self.in_port_size != in_port_size:
            raise ValueError(f"Node template {self.name} "
                             "incompatible with given in port size.")
        return True

    @staticmethod
    def merge_deltablock(other: Optional['NodeTemplate'],
                         body_func: Callable,
                         allow_const: bool,
                         node_key: Optional[str] = None,
                         name: str = None,
                         in_port_size: int = 0,
                         latency: Latency = None,
                         lvl: int = logging.ERROR) -> BodyTemplate:
        """Create a :py:class:`BodyTemplate` for the bodies and constructor
        created using the ``@DeltaBlock`` decorator. Associate this with an
        existing or newly created :py:class:`NodeTemplate`.
        """
        in_params, out_type = get_func_in_params_out_type(
            body_func, False, node_key
        )

        body_template = FuncBodyTemplate(
            name, latency, lvl, body_func, allow_const)
        return NodeTemplate._standardised_merge(other,
                                                body_template,
                                                node_key,
                                                in_port_size,
                                                in_params,
                                                out_type)

    @staticmethod
    def merge_deltamethod(other: Optional['NodeTemplate'],
                          body_func: Callable,
                          node_key: Optional[str] = None,
                          name: str = None,
                          in_port_size: int = 0,
                          latency: Latency = None,
                          lvl: int = logging.ERROR) -> BodyTemplate:
        """Create a :py:class:`BodyTemplate` for the bodies and constructor
        created using the ``@DeltaMethodBlock`` decorator. Associate this with
        an existing or newly created ``NodeTemplate``.
        """
        in_params, out_type = get_func_in_params_out_type(
            body_func, True, node_key,
        )

        body_template = MethodBodyTemplate(name, latency, lvl, body_func)
        return NodeTemplate._standardised_merge(other,
                                                body_template,
                                                node_key,
                                                in_port_size,
                                                in_params,
                                                out_type)

    @staticmethod
    def merge_interactive(other: Optional['NodeTemplate'],
                          func: Callable[[PythonNode], None],
                          in_params: Dict[str, Type],
                          out_type: Type,
                          name: str = None,
                          in_port_size: int = 0,
                          latency: Latency = None,
                          lvl: int = logging.ERROR) -> BodyTemplate:
        """Create a :py:class:`BodyTemplate` for the bodies and constructor
        created using the ``@Interactive`` decorator. Associate this with an
        existing or newly created ``NodeTemplate``.
        """
        if len(in_params) == 0 and out_type == Void:
            raise DeltaIOError('Interactive node must have either an input '
                               'or an output. Otherwise it may freeze '
                               'the runtime simulator.')

        in_params = in_params_as_delta_types(in_params)
        out_type = as_delta_type(out_type)
        body_template = InteractiveBodyTemplate(name, latency, lvl, func)
        return NodeTemplate._standardised_merge(other,
                                                body_template,
                                                node_key=None,
                                                in_port_size=in_port_size,
                                                in_params=in_params,
                                                out_type=out_type)

    @staticmethod
    def merge_migenblock(other: Optional['NodeTemplate'],
                         body_template: BodyTemplate,
                         in_params: Dict[str, Type],
                         out_type: Type,) -> BodyTemplate:
        """Create a :py:class:`BodyTemplate` for the bodies and constructor
        for migen based bodies. Associate this with an existing or newly
        created :py:class:`NodeTemplate`.
        """
        in_params = in_params_as_delta_types(in_params)
        out_type = as_delta_type(out_type)

        return NodeTemplate._standardised_merge(other=other,
                                                body_template=body_template,
                                                in_params=in_params,
                                                out_type=out_type,
                                                node_key=None,
                                                in_port_size=0)

    def call(self, *args, **kwargs):
        """The default call to create a node, can be
        used when no :py:class:`BodyTemplate` exists.
        Tries to construct all bodies in order they were added to the
        template. 
        """
        from ._delta_graph import DeltaGraph
        if DeltaGraph.stack():
            graph = DeltaGraph.current_graph()
        else:
            raise ValueError("Node template called when no graph was active.")

        return self._standardised_call(graph, self.name, self.lvl, None, None,
                                       *args, **kwargs)
