from tempfile import NamedTemporaryFile
import unittest

import deltalanguage as dl

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test._node_lib import send_gates_list_then_exit


class TestExecutionPrimitives(TestExecutionBaseDL):
    """Execute graphs that use primitives defined in ``deltalanguage.lib``."""

    def test_state_saver_save_to_file(self):
        with NamedTemporaryFile(mode="w+") as f:
            store = dl.lib.StateSaver(int, filename=f.name)

            with dl.DeltaGraph() as graph:
                store.save_and_exit(1000)

            self.check_executes_graph(graph)

            f.seek(0)
            self.assertEqual(f.read(), "1000\n")

    def test_loop_with_ProjectQ(self):
        with dl.DeltaGraph() as graph:
            # set up placeholders
            ph_hal_result = dl.placeholder_node_factory()

            int_func = send_gates_list_then_exit.call(
                measurement=ph_hal_result)

            projectQ = dl.lib.HardwareAbstractionLayerNode(
                dl.lib.ProjectqQuantumSimulator(
                    register_size=2,
                    seed=77
                )
            ).accept_command(hal_command=int_func)
            # tie up placeholders
            ph_hal_result.specify_by_node(projectQ)

        self.check_executes_graph(
            graph,
            """\
            Measurement: 4294901760
            """
        )

    def test_loop_with_Qiskit(self):
        """Occasionally fails in Deltasimulator due to a segfault, thus need to
        be fixed.
        """
        with dl.DeltaGraph() as graph:
            ph_hal_result = dl.placeholder_node_factory()

            int_func = send_gates_list_then_exit.call(
                measurement=ph_hal_result)

            qiskit = dl.lib.HardwareAbstractionLayerNode(
                dl.lib.QiskitQuantumSimulator(
                    register_size=2, seed=2
                )
            ).accept_command(int_func)
            # tie up placeholders
            ph_hal_result.specify_by_node(qiskit)

        self.check_executes_graph(graph)


if __name__ == "__main__":
    unittest.main()
