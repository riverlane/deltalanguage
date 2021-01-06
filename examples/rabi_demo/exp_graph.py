from deltalanguage.data_types import DBool, DInt, DUInt, DSize, NoMessage
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import DeltaRuntimeExit
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  placeholder_node_factory,
                                  template_node_factory)

from examples.rabi_demo.aggregator import Aggregator, REPETITIONS, RESOLUTION
from examples.rabi_demo.commander import Commander
from examples.rabi_demo.helper_functions import generate_angles


@DeltaBlock()
def experiment_stopper(completed: DInt(DSize(8))) -> NoMessage:
    if completed:
        if completed == 1:
            raise DeltaRuntimeExit
        else:
            print(f"The experiment returned error code: {completed}")
            raise RuntimeError("Experiment returned an error", completed)


def get_graph():
    """Return the experiments graph `DeltaGraph` and data store instances.

    Note that the aggregator and commanger files can be provided with
    `vcd_name` which will lead to saving VCD of all signals for further
    debugging.
    """
    store = StateSaver(int)

    with DeltaGraph() as graph:
        ph_hal_result = placeholder_node_factory()

        # aggregator node of HAL results
        result_aggregator = Aggregator(
            name="result_aggregator",
            vcd_name=None
        ).call(
            hal_result=ph_hal_result
        )

        # commander node to send HAL instructions
        command_sender = Commander(
            name="command_sender",
            vcd_name=None
        ).call(
            angle=result_aggregator.next_angle
        )

        hal_result = template_node_factory(
            name='QSim',
            command=command_sender.hal_command,
            return_type=DUInt(DSize(32))
        )

        # local store for experiment results
        store.save(result_aggregator.agg_result)

        # tie up placeholders
        ph_hal_result.specify_by_node(hal_result)

        # listen for flag to stop runtime
        experiment_stopper(result_aggregator.completed)

    return graph, store
