"""Testing serialization of DeltaGraph and its componenents."""

import json
import os
import unittest
from unittest.mock import Mock

import capnp
import dill

import deltalanguage.data_types.dotdf_capnp \
    as dotdf_capnp  # pylint: disable=E0401, disable=E0611
from deltalanguage._utils import NamespacedName
from deltalanguage.data_types import (BaseDeltaType,
                                      DOptional,
                                      DInt,
                                      NoMessage,
                                      as_delta_type)
from deltalanguage.lib import StateSaver
from deltalanguage.runtime import (DeltaRuntimeExit,
                                   deserialize_graph,
                                   serialize_graph)
from deltalanguage.wiring import (DeltaBlock,
                                  DeltaGraph,
                                  InPort,
                                  Interactive,
                                  OutPort,
                                  PythonBody,
                                  PyFuncBody,
                                  template_node_factory)

from deltalanguage.lib.hal import HardwareAbstractionLayerNode
from deltalanguage.lib.quantum_simulators import (ProjectqQuantumSimulator,
                                                  QiskitQuantumSimulator)
from test._utils import return_1


class PortSerialisationTest(unittest.TestCase):

    def test_in_port_capnp(self):
        """Generate in port."""
        in_port = InPort(NamespacedName("node_name", "index"),
                         as_delta_type(int), None, 0)
        capnp_in_port = dotdf_capnp.InPort.new_message()
        in_port.capnp(capnp_in_port)
        self.assertEqual(capnp_in_port.name, "index")
        self.assertEqual(dill.loads(capnp_in_port.type), as_delta_type(int))
        self.assertEqual(capnp_in_port.optional, False)

    def test_in_port_capnp_optional(self):
        """Generate optional in port."""
        in_port = InPort(NamespacedName("node_name", "index"),
                         DOptional(int), None, 0)
        capnp_in_port = dotdf_capnp.InPort.new_message()
        in_port.capnp(capnp_in_port)
        self.assertEqual(capnp_in_port.name, "index")
        self.assertEqual(dill.loads(capnp_in_port.type), DInt())
        self.assertEqual(capnp_in_port.optional, True)

    def test_in_port_capnp_wiring(self):
        """Generate wiring."""
        in_port = InPort(NamespacedName("node_name", "index"),
                         as_delta_type(int), None, 0)
        wire = dotdf_capnp.Wire.new_message()
        nodes = [dotdf_capnp.Node.new_message() for _ in range(3)]
        nodes[0].name = "fake_name"
        nodes[1].name = "fake_name"
        nodes[2].name = "node_name"
        nodes[2].init("inPorts", 3)
        nodes[2].inPorts[0].name = "fake_name"
        nodes[2].inPorts[1].name = "index"
        nodes[2].inPorts[2].name = "fake_name"
        in_port.capnp_wiring(nodes, wire)
        self.assertEqual(wire.destNode, 2)
        self.assertEqual(wire.destInPort, 1)
        self.assertEqual(wire.direct, False)

    def test_in_port_capnp_wiring_direct(self):
        """In port has limit on port size."""
        in_port = InPort(NamespacedName("node_name", "index"),
                         as_delta_type(int), None, 1)
        wire = dotdf_capnp.Wire.new_message()
        nodes = [dotdf_capnp.Node.new_message()]
        nodes[0].name = "node_name"
        nodes[0].init("inPorts", 1)
        nodes[0].inPorts[0].name = "index"
        in_port.capnp_wiring(nodes, wire)
        self.assertEqual(wire.destNode, 0)
        self.assertEqual(wire.destInPort, 0)
        self.assertEqual(wire.direct, True)

    def test_out_port_capnp(self):
        """Generate out port."""
        out_port = OutPort(NamespacedName("node_name", "index"),
                           as_delta_type(int), None, None)
        capnp_out_port = dotdf_capnp.OutPort.new_message()
        out_port.capnp(capnp_out_port)
        self.assertEqual(capnp_out_port.name, "index")
        self.assertEqual(dill.loads(capnp_out_port.type), as_delta_type(int))
        with self.assertRaises(AttributeError):
            dummy = capnp_out_port.optional

    def test_out_port_capnp_no_index(self):
        """Generate out port when index not provided.
        In this case, name should be empty string.
        """
        out_port = OutPort(NamespacedName("node_name", None),
                           as_delta_type(int), None, None)
        capnp_out_port = dotdf_capnp.OutPort.new_message()
        out_port.capnp(capnp_out_port)
        self.assertEqual(capnp_out_port.name, "")
        self.assertEqual(dill.loads(capnp_out_port.type), as_delta_type(int))

    def test_out_port_capnp_wiring(self):
        """Generate wiring. Should just call same method in destination."""
        in_port = Mock()
        out_port = OutPort(NamespacedName("node_name", None),
                           as_delta_type(int), in_port, None)
        out_port.capnp_wiring([], None)
        in_port.capnp_wiring.assert_called_with([], None)


class PythonNodeSerialisationTest(unittest.TestCase):

    def setUp(self):
        DeltaGraph.clean_stack()

        @DeltaBlock(allow_const=False)
        def add_print_exit(a: int, b: int) -> NoMessage:
            print(a + b)
            raise DeltaRuntimeExit

        self.func = add_print_exit

    def test_node_serialisation(self):
        """Generate graph and check serialisation is correct."""
        with DeltaGraph() as test_graph:
            self.func(2, 3)

        _, prog = serialize_graph(test_graph)

        self.assertEqual("_".join(prog.nodes[2].name.split("_")[:-1]),
                         "add_print_exit")

        self.assertEqual(prog.nodes[2].body, 2)

        self.assertEqual(prog.nodes[2].inPorts[0].name, "a")
        self.assertEqual(dill.loads(prog.nodes[2].inPorts[0].type),
                         as_delta_type(int))
        self.assertEqual(prog.nodes[2].inPorts[0].optional, False)

        self.assertEqual(prog.nodes[2].inPorts[1].name, "b")
        self.assertEqual(dill.loads(prog.nodes[2].inPorts[1].type),
                         as_delta_type(int))
        self.assertEqual(prog.nodes[2].inPorts[1].optional, False)

        self.assertEqual(len(prog.nodes[2].inPorts), 2)
        self.assertEqual(len(prog.nodes[2].outPorts), 0)

        self.assertEqual(prog.bodies[2].python.dillImpl,
                         test_graph.nodes[2].get_serialised_body())

        self.assertEqual(len(prog.graph), 2)

        self.assertEqual(prog.graph[0].srcNode, 0)
        self.assertEqual(prog.graph[0].srcOutPort, 0)
        self.assertEqual(prog.graph[0].destNode, 2)
        self.assertEqual(prog.graph[0].destInPort, 0)
        self.assertEqual(prog.graph[0].direct, False)

        self.assertEqual(prog.graph[1].srcNode, 1)
        self.assertEqual(prog.graph[1].srcOutPort, 0)
        self.assertEqual(prog.graph[1].destNode, 2)
        self.assertEqual(prog.graph[1].destInPort, 1)
        self.assertEqual(prog.graph[1].direct, False)

    def test_node_serialisation_duplicate_bodies(self):
        """If two blocks share the same body only keep one copy."""
        with DeltaGraph() as test_graph:
            self.func(2, 3)
            self.func(4, 5)

        _, prog = serialize_graph(test_graph)

        self.assertEqual(len(prog.bodies), 5)
        self.assertEqual(prog.nodes[2].body, prog.nodes[5].body)

    def test_splitter_serialisation(self):
        """Splitter nodes should be added when serialising."""
        @DeltaBlock(allow_const=False)
        def add(a: int, b: int) -> int:
            return a+b
        with DeltaGraph() as test_graph:
            a = add(2, 3)
            self.func(a, 4)
            self.func(a, 5)

        _, prog = serialize_graph(test_graph)

        splitter_body = dill.loads(prog.bodies[-1].python.dillImpl)
        self.assertEqual(type(splitter_body), PyFuncBody)
        self.assertEqual(len(prog.nodes), 8)

    def test_interactive_serialisation(self):
        """Interactive nodes have their own serialised body type.

        This is to distinguish their bodies from Python bodies, as they
        take different inputs.
        """
        @Interactive(in_params={'a': int, 'b': int}, out_type=NoMessage)
        def add(node) -> int:
            a = node.receive('a')
            b = node.receive('b')
            print(a+b)
            raise DeltaRuntimeExit
        with DeltaGraph() as test_graph:
            a = add.call(a=2, b=3)

        _, prog = serialize_graph(test_graph)

        self.assertEqual(prog.bodies[0].which(), 'interactive')
        interactive_body = prog.bodies[0].interactive.dillImpl
        self.assertEqual(interactive_body, a.get_serialised_body())

    def test_projectQ_serialisation(self):
        """Test ProjectQ nodes serialization/deserialization.

        ProjectQ can't be fully serialized, we need to exclude from dill the
        engine (c++ libraries). This test is to guarantee that when we deserialize
        everything works as expected.
        """

        with DeltaGraph() as test_graph:
            projectQ = HardwareAbstractionLayerNode(
                ProjectqQuantumSimulator(register_size=2)).accept_command(command=0x4000000)

        data, prog = serialize_graph(test_graph)
        g_capnp = deserialize_graph(data)

        # Checking that we are investigating the right node.
        self.assertEqual(g_capnp.nodes[1].name.split("_")[0], "accept")
        body = g_capnp.bodies[1].python.dillImpl

        node = dill.loads(body)
        node.eval(command=0x4000000)

    def test_qiskit_serialisation(self):
        """Test Qiskit nodes serialization/deserialization.

        """

        with DeltaGraph() as test_graph:
            qiskit = HardwareAbstractionLayerNode(
                QiskitQuantumSimulator(register_size=2)).accept_command(command=0x4000000)

        data, prog = serialize_graph(test_graph)
        g_capnp = deserialize_graph(data)

        # Checking that we are investigating the right node.
        self.assertEqual(g_capnp.nodes[1].name.split("_")[0], "accept")
        body = g_capnp.bodies[1].python.dillImpl
        node = dill.loads(body)
        node.eval(command=0x4000000)

    def test_template_node_capnp(self):
        """Test TemplateNode.

        TODO: use serialize_graph
        """
        with DeltaGraph() as test_graph:
            template_node_factory(
                a=1, b=2, return_type=int, name="temp-test"
            )

        prog = dotdf_capnp.Program.new_message()
        bodies = prog.init_resizable_list("bodies")
        nodes = prog.init("nodes", len(test_graph.nodes))
        for node, capnp_node in zip(test_graph.nodes, nodes):
            node.capnp(capnp_node, bodies)

        self.assertEqual(nodes[2].name.split("_")[0], "template")
        self.assertEqual(nodes[2].name.split("_")[1], "temp-test")
        self.assertEqual(nodes[2].body, -1)

    def test_serialisation(self):
        """Serialize/deserialize a graph.

        Notes
        -----
        The content of the bodies depends on the environment, i.e. how the test
        is executed. For this reason we just compare the structure of the graph
        here.
        """
        with DeltaGraph() as graph:
            self.func(40, 2)

        data, _ = serialize_graph(graph)
        self.assertEqual(type(data), bytes)
        g_capnp = deserialize_graph(data).to_dict()
        for body in g_capnp['bodies']:
            if 'python' in body:
                self.assertTrue(isinstance(dill.loads(
                    body['python']['dillImpl']), PythonBody))
                del body['python']['dillImpl']
        for node in g_capnp['nodes']:
            for port in node['inPorts'] + node['outPorts']:
                self.assertTrue(isinstance(
                    dill.loads(port['type']), BaseDeltaType))
                del port['type']
        with open('test/data/graph_capnp.json', 'r') as file:
            self.assertEqual(g_capnp, json.load(file))


class FileSerialisationTest(unittest.TestCase):
    """Tests of serialised files."""

    def setUp(self):
        """Set up a simple graph"""
        saver = StateSaver()
        with DeltaGraph() as test_graph:
            saver.save_and_exit(return_1())
        self.graph = test_graph

    def assert_correct_serialisation(self, prog, files):
        self.assertEqual(len(prog.files), len(files))
        for capnp_file, file in zip(prog.files, files):
            self.assertEqual(capnp_file.name, file)
            with open(file, "rb") as test_file:
                self.assertEqual(capnp_file.content, test_file.read())

    def test_serialisation_no_file(self):
        """Generate serialisation without file attached."""
        _, prog = serialize_graph(self.graph)
        self.assert_correct_serialisation(prog, [])

    def test_serialisation_with_file(self):
        """Generate serialisation with file attached."""
        files = [os.path.join("deltalanguage", "lib", "primitives.py")]
        _, prog = serialize_graph(self.graph,
                                  files=files)
        self.assert_correct_serialisation(prog, files)

    def test_serialisation_multiple_files(self):
        """Generate serialisation with several files attached."""
        files = [os.path.join("deltalanguage", "lib", "primitives.py"),
                 os.path.join("deltalanguage", "runtime", "_output.py"),
                 os.path.join("deltalanguage", "__about__.py")]
        _, prog = serialize_graph(self.graph,
                                  files=files)
        self.assert_correct_serialisation(prog, files)

    def test_serialisation_nonpy_files(self):
        """Generate serialisation with non-Python files attached."""
        files = [os.path.join("deltalanguage", "DeltaStyle.xml"),
                 os.path.join("test", "data", "graph_capnp.json"),
                 os.path.join("examples", "tutorials", "const_nodes.ipynb"),
                 os.path.join("docs", "figs", "blocks.png")]
        _, prog = serialize_graph(self.graph,
                                  files=files)
        self.assert_correct_serialisation(prog, files)


if __name__ == "__main__":
    unittest.main()
