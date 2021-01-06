import logging
from typing import Dict, Type, Union

from deltalanguage.data_types import BaseDeltaType

from ._delta_graph import DeltaGraph
from ._node_classes.template_node import TemplateNode
from ._node_classes.real_nodes import as_node


def template_node_factory(
    return_type: Union[Type, BaseDeltaType] = None,
    name: str = None,
    arg_types: Dict[str, Union[Type, BaseDeltaType]] = {},
    lvl: int = logging.ERROR,
    **kwargs
) -> TemplateNode:
    """Node factory for :py:class:`TemplateNode`.

    When used the inputs and outputs types should be provided, please see the
    examples for use cases.

    Parameters
    ----------
    return_type : Union[Type, BaseDeltaType]
        The required output from the implemented body of this node.
    name
        Name for the template node.
    arg_types : Dict[str, Union[Type, BaseDeltaType]]
        The types of each in port. Required if input nodes do not have a
        specified type, such as with placeholder nodes.
    kwargs
        Nodes to create in-ports for by kw.

    Returns
    -------
    TemplateNode
        Template for a node.


    Examples
    --------
    This superficial example illustrates the power of templates, which
    lies in the fact that the running stage can be done one any runtime system
    and that the implementation of template nodes is completely isolated from
    application developers who work only at the programming stage:

    .. code-block:: python

        >>> from deltalanguage.lib import StateSaver
        >>> from deltalanguage.runtime import DeltaPySimulator
        >>> from deltalanguage.wiring import (DeltaBlock, DeltaGraph,
        ...                                   template_node_factory)

        >>> @DeltaBlock()
        ... def foo(a: int, b: int) -> int:
        ...     return a + b

        >>> s = StateSaver(int, verbose=True)

        # programming stage: define a graph with a template node
        >>> with DeltaGraph() as graph:
        ...     n = template_node_factory(a=1, b=2, return_type=int)
        ...     s.save_and_exit(n) # doctest:+ELLIPSIS
        save_and_exit...

        # running stage: complete the graph by specifying templates and run
        >>> n.specify_by_func(foo)
        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        saving 3


    """

    # Get the active graph from the top of the graph stack
    graph = DeltaGraph.current_graph()

    # Check if arguments are nodes.
    # If not, put them in PyConstNodes in the current graph
    kw_input_nodes = {name: as_node(arg, graph)
                      for (name, arg) in kwargs.items()}

    # Use TemplateNode constructor and return result
    return TemplateNode(
        graph,
        kw_input_nodes,
        return_type,
        name,
        arg_types,
        lvl=lvl
    )
