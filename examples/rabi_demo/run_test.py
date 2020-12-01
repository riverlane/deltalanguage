"""This file exists for purely testing of Deltaflow-on-ARTIQ.

For an explanation please read the notebook, which has much more details.
"""

from deltalanguage.lib import (HardwareAbstractionLayerNode,
                               ProjectqQuantumSimulator)
from deltalanguage.runtime import DeltaPySimulator

from examples.rabi_demo.exp_graph import get_graph
from examples.rabi_demo.aggregator import REPETITIONS, RESOLUTION


graph, store = get_graph()

q_sim = HardwareAbstractionLayerNode(
    ProjectqQuantumSimulator(register_size=1)
)
template_node = graph.find_node_by_name('template_QSim')
template_node.specify_by_func(q_sim.accept_command)

print(graph)

rt = DeltaPySimulator(graph)
rt.run()

# basic checks
assert len(store.saved) == 2**RESOLUTION
assert all(map(lambda x: x <= REPETITIONS, store.saved))
