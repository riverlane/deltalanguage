import dill

import deltalanguage as dl


@dl.DeltaBlock(name="add", allow_const=False)
def add(a: int, b: int) -> int:
    return a + b


@dl.DeltaBlock(name="print_exit", allow_const=False)
def print_then_exit(to_print: object) -> dl.Void:
    print(to_print)
    raise dl.DeltaRuntimeExit


with dl.DeltaGraph() as graph:
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
