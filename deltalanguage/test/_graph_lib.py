"""Collection of graphs used in one or more unittests.
"""

import deltalanguage as dl
from deltalanguage.test._node_lib import (add_const,
                                          add_optional,
                                          add_non_const,
                                          forward_const,
                                          forward_non_const,
                                          return_nothing,
                                          return_1_const,
                                          return_2_const,
                                          return_1_2_const)


def getg_const_chain():
    """Return a graph with multiple constant nodes connected in sequence.
    """
    s = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        n0 = return_2_const()
        n1 = forward_const(n0)
        n2 = forward_non_const(n1)
        s.save_and_exit(n2)

    return graph


def getg_optional_queues():
    """Return a graph where there is one output to an optional
    in-port.
    """
    s = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        n0 = return_nothing()
        n1 = return_2_const()
        n2 = add_optional(n0, n1)
        s.save_and_exit(n2)

    return graph


def getg_PyFunc_body_graph():
    """Return a basic graph with a non-const PyFuncBody.
    """
    s = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        s.save_and_exit(add_non_const(2, 3))

    return graph


def getg_PyInteractiveBody_one_in_one_out():
    """Return a graph that has a PyInteractiveBody with one input
    and one output.
    """
    @dl.Interactive([("num", int)], [("output", int)])
    def interactive_func(node: dl.PythonNode):
        for _ in range(2):
            num = node.receive("num")
            print(f"received num: {num}")
        node.send(num + 1)

    s = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        s.save_and_exit(interactive_func.call(add_non_const(2, 3)))

    return graph


def getg_PyInteractiveBody_one_in_two_out():
    """Return a graph that has a PyInteractiveBody with one input
    and two outputs.
    """
    @dl.Interactive(
        [("num", dl.Int(dl.Size(32)))],
        [('num_out', dl.Int(dl.Size(32))), ('val_out', dl.Bool())]
    )
    def interactive_func(node: dl.PythonNode):
        for _ in range(2):
            num = node.receive("num")
            print(f"received num: {num}")
        node.send(num_out=None, val_out=False)
        node.send(num_out=14, val_out=False)

    s0 = dl.lib.StateSaver(bool, condition=lambda x: x)
    s1 = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        int_func = interactive_func.call(4)
        s0.save_and_exit_if(int_func.val_out)
        s1.save_and_exit(int_func.num_out)

    return graph


def getg_PyInteractiveBody_two_in_one_out():
    """Return a graph that has a PyInteractiveBody with two inputs
    and one output.
    """
    @dl.Interactive([("num", dl.Int(dl.Size(32))),
                     ("opt_val", dl.Optional(dl.Bool()))],
                    [("output", dl.Bool())])
    def interactive_func(node: dl.PythonNode):
        for _ in range(2):
            num = node.receive("num")
            opt_val = node.receive("opt_val")
            print(f"received opt_val: {opt_val}")
            print(f"received num: {num}")
        node.send(True)

    s = dl.lib.StateSaver(bool, verbose=True, condition=lambda x: x)

    with dl.DeltaGraph() as graph:
        int_func = interactive_func.call(num=4, opt_val=True)
        s.save_and_exit_if(int_func)

    return graph


def getg_PyInteractiveBody_two_in_two_out():
    """Return a graph that has a PyInteractiveBody with two inputs
    and two outputs.
    """
    @dl.Interactive([("num", dl.Int(dl.Size(32))),
                     ("opt_val", dl.Optional(dl.Bool()))],
                    [('num_out', dl.Int(dl.Size(32))),
                     ('val_out', dl.Bool())])
    def interactive_func(node: dl.PythonNode):
        for _ in range(2):
            num = node.receive("num")
            opt_val = node.receive("opt_val")
            print(f"received opt_val: {opt_val}")
            print(f"received num: {num}")
        node.send(num_out=None, val_out=False)
        node.send(num_out=14, val_out=False)

    s0 = dl.lib.StateSaver(bool, condition=lambda x: x)
    s1 = dl.lib.StateSaver(int, verbose=True)

    with dl.DeltaGraph() as graph:
        int_func = interactive_func.call(num=4, opt_val=True)
        s0.save_and_exit_if(int_func.val_out)
        s1.save_and_exit(int_func.num_out)

    return graph


def getg_optional_const():
    """Return a graph where a constant node is outputting to an optional
    in-port.
    """
    n_iter = 1000
    s = dl.lib.StateSaver(int, verbose=True)
    gen = dl.lib.make_generator(1, reps=n_iter)

    @dl.Interactive([('a', int)], [('out', int)])
    def aggregator(node):
        result = 0
        for _ in range(n_iter):
            a = node.receive('a')
            result += a
        node.send(result)

    with dl.DeltaGraph() as graph:
        total = add_optional(return_1_const(), gen.call())
        s.save_and_exit(aggregator.call(a=total))

    return graph


def getg_splitting_const_const_same():
    """Return a graph where we split a constant node output to the same
    constant node.
    """
    s = dl.lib.StateSaver(int, verbose=True)
    with dl.DeltaGraph() as graph:
        val = return_1_const()
        s.save_and_exit(add_const(val, val))

    return graph


def getg_splitting_const_const_same_and_diff():
    """Return a graph where we split a constant node output to the same
    constant node and also to a different constant node.
    """
    s = dl.lib.StateSaver(int, verbose=True)
    with dl.DeltaGraph() as graph:
        val = return_1_2_const()
        s.save_and_exit(
            add_const(
                add_const(
                    add_const(
                        val.x,
                        val.x
                    ),
                    val.y),
                val.y
            )
        )

    return graph
