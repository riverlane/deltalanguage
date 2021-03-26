"""It's so intense.

More complicated version of the interactive_console demo.

Two blocks each running their own interactive console and communicating with
each other.

To exit, use node.send(-1) to terminate one block and raise the
DeltaRuntimeExit and then press Ctrl-D (Linux/MacOS) or Ctrl-Z (Windows) twice
to ensure the other block terminates too.
"""

import code
from collections import OrderedDict

import deltalanguage as dl

X = 4
Y = 5
Z = 6


@dl.DeltaBlock(node_key="node", allow_const=False)
def interact(a: int,
             b:  dl.Optional(int) = None,
             node: dl.PythonNode = None) -> int:
    """Node that will set up an interactive console.

    The user will be able to see local variables, arguments and globals.

    Through the node object, they can also send & receive messages.

    Args:
        a : int
            An argument the user can access (either 1 or 2 to distinguish
            the two nodes)
        b : int
            An argument sent from one node to the other
    """
    c = 9
    d = 10
    if b == -1:
        raise dl.DeltaRuntimeExit
    code.interact(
        banner=f"{a}",
        local=dict(globals(), **locals()),
        exitmsg=f"Exiting {a}"
    )


if __name__ == "__main__":
    # define our two-cycle graph
    with dl.DeltaGraph() as test_graph:
        p = dl.placeholder_node_factory()
        n1 = interact(a=1, b=p)
        n2 = interact(a=2, b=n1)
        p.specify_by_node(n2)

    # make a runtime and run the graph
    rt = dl.DeltaPySimulator(test_graph)
    rt.run()
