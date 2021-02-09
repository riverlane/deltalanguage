import dill

from deltalanguage.data_types import NoMessage
from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import DeltaBlock, DeltaGraph


@DeltaBlock(name="add", allow_const=False)
def add(a: int, b: int) -> int:
    return a + b


@DeltaBlock(name="print_exit", allow_const=False)
def print_then_exit(to_print: object) -> NoMessage:
    print(to_print)
    raise DeltaRuntimeExit


with DeltaGraph() as graph:
    added = add(a=4, b=3)
    print_then_exit(to_print=added)

# take out the node that has the add function
node = graph.nodes[2]

# serialise it
serialised = node.body.as_serialised

# <send serialised object down the wire here>

# deserialise
deserialised_node_body = dill.loads(serialised)

# check the function
val = deserialised_node_body.eval(4, 3)
print(val)

assert val == 7
