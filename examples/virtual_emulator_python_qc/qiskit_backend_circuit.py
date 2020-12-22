import numpy as np
from deltalanguage.data_types import DArray, DUInt, DSize
from deltalanguage.lib.hal import (command_creator,
                                   HardwareAbstractionLayerNode,
                                   measurement_unpacker)
from deltalanguage.lib.quantum_simulators import QiskitQuantumSimulator
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.wiring import (DeltaGraph,
                                  DeltaMethodBlock,
                                  Interactive,
                                  placeholder_node_factory,
                                  PyInteractiveNode,
                                  template_node_factory)


### ---------------------------- CONSTRUCT NODES -------------------------- ###
# One node to send circuit to HAL node, another to digest result from HAL node
@Interactive(
    {"input_params": DArray(int, DSize(2)), "repeat": bool}, DUInt(DSize(32))
)
def send_gate_sequence(node: PyInteractiveNode):
    """Interactive node to define the circuit.
    Accepts the circuit parameters and sends the HAL commands to the HAL node.

    Parameters
    ----------
    node : PyInteractiveNode
        The node that sends the HAL command outputs.
    """

    params = node.receive("input_params")
    repeat = True

    # send each gate at least once
    while repeat:

        node.send(command_creator("STATE_PREPARATION"))
        node.send(
            command_creator("RX", argument=params[0])
        )
        node.send(
            command_creator("RZ", argument=params[1])
        )
        node.send(
            command_creator("RY", argument=params[2])
        )
        node.send(
            command_creator("R", qubit=0)
        )
        node.send(
            command_creator("PIXY", argument=params[3])
        )
        node.send(
            command_creator("PIYZ", argument=params[4])
        )
        node.send(
            command_creator("PIZX", argument=params[5])
        )
        node.send(
            command_creator("H", qubit=0)
        )
        node.send(
            command_creator("S", qubit=1)
        )
        node.send(
            command_creator("SQRT_X", qubit=0)
        )
        node.send(
            command_creator("T", qubit=1)
        )
        node.send(
            command_creator("X", qubit=0)
        )
        node.send(
            command_creator("Y", qubit=1)
        )
        node.send(
            command_creator("Z", qubit=0)
        )
        node.send(
            command_creator("INVS", qubit=1)
        )
        node.send(
            command_creator("SX", qubit=0)
        )
        node.send(
            command_creator("SY", qubit=1)
        )
        node.send(
            command_creator("CONTROL", qubit=0)
        )
        node.send(
            command_creator("X", qubit=1)
        )
        node.send(command_creator("STATE_MEASURE"))

        repeat = node.receive("repeat")


class Aggregator:
    """Class that maintains the state of the results received from the
    HAL node.
    """

    def __init__(self, repetitions: int = 1):
        """Constructor

        Parameters
        ----------
        repetitions : int, optional
            The number of measurement results required for the statistics,
            by default 1
        """
        self._repetitions = repetitions
        self._counter = 0
        self._results = []

    @DeltaMethodBlock(name="result_collector")
    def result_collector(self, result: DUInt(DSize(32))) -> bool:
        """Method to receive the results and update state.

        Parameters
        ----------
        result : int
            Result from quantum HAL node.

        Returns
        -------
        bool
            Flag to signal to the circuit node to send again.

        Raises
        ------
        DeltaRuntimeExit
            Stops the deltaflow program when statistics have been aggregated
        """
        measurement = measurement_unpacker(result, [0])
        self._results.append(measurement)
        self._counter += 1

        if self._counter == self._repetitions:

            print(
                "Expectation value: " +
                f"{np.round(np.sum(self._results) / self._repetitions, 1)}"
            )

            raise DeltaRuntimeExit

        return True


### -------------------------- BUILD DELTAGRAPH -------------------------- ###

# 0 = 0 rad; 256 = pi/2 rad; 512 = pi rad; 768 = 3pi/2 rad;
# 1023 (max value) = 2pi * (1 - 1/1024) rad, i.e almost 2pi rad
params = [586, 548, 215, 484, 832, 421]
repetitions = 3

aggregator = Aggregator(repetitions=repetitions)


with DeltaGraph() as graph:
    ph = placeholder_node_factory()
    sender_node = send_gate_sequence.call(input_params=params, repeat=ph)
    hal_node = template_node_factory(
        command=sender_node,
        return_type=DUInt(DSize(32))
    )
    agg = aggregator.result_collector(result=hal_node)
    ph.specify_by_node(agg)

# specify the hal_node body
q_sim = HardwareAbstractionLayerNode(
    QiskitQuantumSimulator(register_size=2, seed=9324)
)
hal_node.specify_by_func(q_sim.accept_command)

rt = DeltaPySimulator(graph)
rt.run()
