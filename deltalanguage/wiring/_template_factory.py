import logging
from typing import Dict, Type, Union

from deltalanguage.data_types import BaseDeltaType, as_delta_type

from ._delta_graph import DeltaGraph
from ._node_classes.abstract_node import ForkedNode
from ._node_classes.node_bodies import TemplateBody
from ._node_classes.placeholder_node import PlaceholderNode
from ._node_classes.real_nodes import as_node, PythonNode


def template_node_factory(
    out_type: Union[Type, BaseDeltaType] = None,
    name: str = None,
    arg_types: Dict[str, Union[Type, BaseDeltaType]] = {},
    lvl: int = logging.ERROR,
    **kwargs
) -> PythonNode:
    """Node factory for nodes with :py:class:`TemplateBody`.

    When used the inputs and outputs types should be provided, please see the
    examples for use cases.

    Parameters
    ----------
    out_type : Union[Type, BaseDeltaType]
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
    PythonNode
        With a body that can be replaced with another body (a template body)


    Examples
    --------
    This superficial example illustrates the power of templates, which
    lies in the fact that the running stage can be done on any runtime
    simulator or runtime system and that the implementation of template nodes
    is can be added later.
    This is handy if commercial drivers are not accessible for an application
    developer:

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock()
        ... def foo(a: int, b: int) -> int:
        ...     return a + b

        >>> s = dl.lib.StateSaver(int, verbose=True)

        # programming stage: define a graph with a template node
        >>> with dl.DeltaGraph() as graph:
        ...     n = dl.template_node_factory(a=1, b=2, out_type=int)
        ...     s.save_and_exit(n) # doctest:+ELLIPSIS
        save_and_exit...

        # running stage: complete the graph by specifying templates and run
        >>> n.specify_by_func(foo)
        >>> rt = dl.DeltaPySimulator(graph)
        >>> rt.run()
        saving 3


    """

    # Get the active graph from the top of the graph stack
    graph = DeltaGraph.current_graph()

    # Check if arguments are nodes.
    # If not, put them in PyConstBodies in the current graph
    kw_in_nodes = {name: as_node(arg, graph)
                   for (name, arg) in kwargs.items()}

    name_prefix = "template"

    if name is not None:
        name_prefix = name_prefix + "_" + name

    # Construct the in paramters dict from the kw_in_nodes
    in_params = {}
    for k, v in kw_in_nodes.items():
        # First check if input type specified in arg_types
        if k in arg_types:
            arg_type = as_delta_type(arg_types[k])
        else:
            arg_type = None
        # Now check if input type is specified in nodes
        if isinstance(v, ForkedNode):
            # In input type is forked, then get specified port type
            ret_type = v.out_type.elem_dict[v.index]
        else:
            ret_type = v.out_type

        if not isinstance(ret_type, BaseDeltaType):
            # If we get here then type is not specified
            ret_type = None
        if (arg_type is not None) and (ret_type is not None):
            # We have type define in arg_types and input
            # check if they match
            if arg_type == ret_type:
                in_params[k] = arg_type
            else:
                raise TypeError(f"Argument {k} specified as {arg_type}"
                                f" but is actually {ret_type}")
        elif arg_type is not None:
            # TODO: think this is only necessary to pass a test
            if isinstance(v, PlaceholderNode):
                v.out_type = arg_type
            in_params[k] = arg_type
        elif ret_type is not None:
            in_params[k] = ret_type
        else:
            # Type cannot be found
            raise TypeError(f"No type specified for argument {k}")

    constructed_body = TemplateBody(kw_in_nodes)

    return PythonNode(graph,
                      [constructed_body],
                      in_params,
                      [],
                      kw_in_nodes,
                      out_type=as_delta_type(out_type),
                      name=name_prefix,
                      lvl=lvl)
