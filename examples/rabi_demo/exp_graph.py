import deltalanguage as dl

from examples.rabi_demo.aggregator import Aggregator, REPETITIONS, RESOLUTION
from examples.rabi_demo.commander import Commander
from examples.rabi_demo.helper_functions import generate_angles


@dl.DeltaBlock()
def experiment_stopper(completed: dl.Int(dl.Size(8))) -> dl.Void:
    if completed:
        if completed == 1:
            raise dl.DeltaRuntimeExit
        else:
            print(f"The experiment returned error code: {completed}")
            raise RuntimeError("Experiment returned an error", completed)


def get_graph():
    """Return the experiments graph `DeltaGraph` and data store instances.

    Note that the aggregator and commanger files can be provided with
    `vcd_name` which will lead to saving VCD of all signals for further
    debugging.
    """
    result_storage = dl.lib.StateSaver(int)
    cmds_storage = dl.lib.StateSaver(dl.UInt(dl.Size(32)))
    hal_template = dl.lib.hal_template

    with dl.DeltaGraph() as graph:
        ph_hal_result = dl.placeholder_node_factory()
        ph_commander = dl.placeholder_node_factory()

        # aggregator node of HAL results
        result_aggregator = Aggregator(
            name="result_aggregator",
            vcd_name=None
        ).call(
            hal_result=ph_hal_result,
            shot_completed=ph_commander.shot_completed
        )

        # commander node to send HAL instructions
        command_sender = Commander(
            name="command_sender",
            vcd_name=None
        ).call(
            angle=result_aggregator.next_angle
        )

        hal_result = hal_template.call(hal_command=command_sender.hal_command)

        # local store for experiment results
        result_storage.save(result_aggregator.agg_result)
        cmds_storage.save(command_sender.hal_command)

        # tie up placeholders
        ph_hal_result.specify_by_node(hal_result)
        ph_commander.specify_by_node(command_sender)

        # listen for flag to stop runtime
        experiment_stopper(result_aggregator.completed)

    return graph, result_storage, cmds_storage
