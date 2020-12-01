"""Interactive console example.

Starts an interactive console in a node, so the user can check their
environment when debugging.

The user can also send and receive messages in the interactive console
via node.send() and node.receive() commands, just like in interactive
nodes.

To exit, first send -1 to the printer node, using

node.send(-1)

Then exit the Python console the standard way
(Ctrl-D on Linux/MacOS, Ctrl-Z on Windows).
"""

import code
from collections import OrderedDict

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaRuntimeExit, DeltaPySimulator
from deltalanguage.wiring import DeltaBlock, DeltaGraph, PythonNode

X = 4
Y = 5
Z = 6


@DeltaBlock(node_key="node", allow_const=False)
def interact(a: int, b: int, node: PythonNode = None) -> int:
    """Node that will set up an interactive console.

    The user will be able to see local variables, arguments and globals.

    Through the node object, they can also send & receive messages.

    Exiting the console via Ctrl-D or Ctrl-Z will cause another console
    to be set up if a runtime is still running. If the printer node has
    raised a DeltaRuntimeExit (done by sending -1 from this node)
    then exiting the console will terminate the program.

    Args:
        a : int
            An argument the user can access
        b : int
            Another argument the user can access
        node : Optional[PythonFuncNode]
            The node this block is running on. Used so that the user can send
            & receive messages in the interactive console.
    """
    c = 9
    d = 10
    code.interact(local=dict(globals(), **locals()))


@DeltaBlock()
def printer(n: int) -> NoMessage:
    if n == -1:
        print("Exiting Deltaflow example")
        print("Exit the console via"
              + " Ctrl-D on Linux/MacOS or Ctrl-Z on Windows")
        raise DeltaRuntimeExit
    print(n)


if __name__ == "__main__":
    # define our DeltaGraph
    with DeltaGraph() as test_graph:
        n = interact(7, 8)
        printer(n)

    # make a runtime and run the graph
    rt = DeltaPySimulator(test_graph)
    rt.run()
