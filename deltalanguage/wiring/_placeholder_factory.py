from ._delta_graph import DeltaGraph
from ._node_classes.placeholder_node import PlaceholderNode
from ._node_classes.real_nodes import as_node


def placeholder_node_factory(*args, name=None, **kwargs) -> PlaceholderNode:
    """Node factory for for :py:class:`PlaceholderNode`.

    The main use case of such nodes is allowing us to create cycles
    in :py:class:`DeltaGraph` by allowing data dependencies to be resolved
    out of the order. The need for this step

    Parameters
    ----------
    args
        Nodes to create in-ports for if needed.
    name
        Name for the placeholder.
    kwargs
        Nodes to create in-ports for by kw if needed.

    Returns
    -------
    PlaceholderNode
        Constructed placeholder node.


    Examples
    --------
    In this example we see a simple cycle of 2 nodes.
    The placeholder is first used to provide an input to a new node, and then
    it is specified by :py:meth:`PlaceholderNode.specify_by_node`:

    .. code-block:: python

        >>> from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
        >>> from deltalanguage.wiring import (DeltaBlock, DeltaGraph,
        ...                                   Interactive,
        ...                                   placeholder_node_factory)

        >>> @DeltaBlock()
        ... def foo(a: int) -> int:
        ...     if a%2 == 0:
        ...         return a
        ...     else:
        ...         return -a

        >>> @Interactive(in_params={"a": int}, out_type=int)
        ... def bar(node):
        ...     internal_memory = 0
        ...
        ...     for i in range(5):
        ...         node.send(i)
        ...         internal_memory += node.receive("a")
        ...
        ...     print("0 - 1 + 2 - 3 + 4 =", internal_memory)
        ...     raise DeltaRuntimeExit

        >>> with DeltaGraph() as graph:
        ...     p = placeholder_node_factory()
        ...     b = bar.call(a=p)
        ...     p.specify_by_node(foo(b))

        >>> rt = DeltaPySimulator(graph)
        >>> rt.run()
        0 - 1 + 2 - 3 + 4 = 2

    .. warning::
        It is very important to design graphs in such a way that the exit
        condition
        :py:class:`DeltaRuntimeExit<deltalanguage.runtime.DeltaRuntimeExit>`
        can always be reached.
        For graphs with cyclic dependency of nodes it means that at least
        one node should contain an internal state that would terminate the
        cycle and redirect the flow of data in the graph.
        Formally it means that the graph of nodes (which might be cyclic) has
        a representation as a graph of states (which must be acyclic).

        In the example above the state of the graph changes at each cycle,
        with a clear termination condition, i.e. when ``for`` loop terminates.

        In case if nodes have non-determinism, the designer of the graph
        might need to think about a backup exit plan, such as timeout or a
        maximum number of iterations.
        For instance, the python runtime's method
        :py:meth:`DeltaPySimulator.run<deltalanguage.runtime.DeltaPySimulator.run>`
        can be provided with the maximum number of iteration cycles.

    Also users can define placeholders by a usual python functions
    of class methods via :py:meth:`PlaceholderNode.specify_by_func` and
    :py:meth:`PlaceholderNode.specify_by_method` respectively.

    .. TODO:: Add examples for both cases.
    """
    # Get an appropriate name
    if name is None:
        name = DeltaGraph.get_next_placeholder_name()

    # Get the active graph from the top of the graph stack
    graph = DeltaGraph.current_graph()

    # Check if arguments are nodes.
    # If not, put them in PyConstNodes in the current graph
    pos_input_nodes = [as_node(arg, graph) for arg in args]
    kw_input_nodes = {name: as_node(arg, graph)
                      for (name, arg) in kwargs.items()}

    # Use PlaceholderNode constructor and return result
    return PlaceholderNode(graph, name, *pos_input_nodes, **kw_input_nodes)
