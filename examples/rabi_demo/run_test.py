"""This file exists for purely testing of Deltaflow-on-ARTIQ.

For an explanation please read the notebook, which has much more details.
"""

import deltalanguage as dl

from examples.rabi_demo.exp_graph import get_graph
from examples.rabi_demo.aggregator import REPETITIONS, RESOLUTION


graph, result_storage, cmds_storage = get_graph()

q_sim = dl.lib.HardwareAbstractionLayerNode(
    dl.lib.ProjectqQuantumSimulator(register_size=1)
)
template_node = graph.find_node_by_name('template_QSim')
template_node.specify_by_func(q_sim.accept_command)

print(graph)

rt = dl.DeltaPySimulator(graph)
rt.run()

# basic checks
assert len(result_storage.saved) == 2**RESOLUTION, \
    f"{len(result_storage.saved)} /= {2**RESOLUTION}"
assert len(cmds_storage.saved) == 3 * 2**RESOLUTION * REPETITIONS, \
    f"{len(cmds_storage.saved)} /= {3 * 2**RESOLUTION * REPETITIONS}"
assert all(map(lambda x: x <= REPETITIONS, result_storage.saved))
