import unittest

import deltalanguage as dl
from deltalanguage import DeltaRuntimeExit

from deltalanguage.test.execution.base import TestExecutionBaseDL
from deltalanguage.test.test_types import RecATI


class TestExecutionTypes(TestExecutionBaseDL):
    """Test that all supported data types can be passed as messages
    during ``DeltaGraph`` execution.
    """

    def test_primitives(self):
        tuple_int = dl.Tuple([
            dl.Int(dl.Size(8)),
            dl.Int(dl.Size(16)),
            dl.Int(dl.Size(32)),
            dl.Int(dl.Size(64))
        ])
        tuple_uint = dl.Tuple([
            dl.UInt(dl.Size(8)),
            dl.UInt(dl.Size(16)),
            dl.UInt(dl.Size(32)),
            dl.UInt(dl.Size(64))
        ])
        tuple_float = dl.Tuple([
            dl.Float(dl.Size(32)),
            dl.Float(dl.Size(64))
        ])
        tuple_complex = dl.Tuple([
            dl.Complex(dl.Size(64)),
            dl.Complex(dl.Size(128))
        ])
        tuple_bool_char = dl.Tuple([
            dl.Bool(),
            dl.Str(dl.Size(1))
        ])

        @dl.Interactive([("ack_int", bool),
                         ("ack_uint", bool),
                         ("ack_float", bool),
                         ("ack_complex", bool),
                         ("ack_bool_char", bool)],
                        [("out_int", tuple_int),
                         ("out_uint", tuple_uint),
                         ("out_float", tuple_float),
                         ("out_complex", tuple_complex),
                         ("out_bool_char", tuple_bool_char)])
        def testbench(node: dl.PythonNode):
            node.send(out_int=(-128, -32768, -2147483648, -9223372036854775808))
            assert node.receive("ack_int")

            node.send(out_int=(127, 32767, 2147483647, 9223372036854775807))
            assert node.receive("ack_int")

            node.send(out_uint=(0, 0, 0, 0))
            assert node.receive("ack_uint")

            node.send(out_uint=(255, 65535, 4294967295, 18446744073709551615))
            assert node.receive("ack_uint")

            # this is just a rough estimate
            node.send(out_float=(1.0000001, 1.000000000000001))
            assert node.receive("ack_float")

            node.send(out_complex=((1.0000001+1.0000001j),
                                   (1.000000000000001+1.000000000000001j)))
            assert node.receive("ack_complex")

            node.send(out_bool_char=(True, 'a'))
            assert node.receive("ack_bool_char")

            raise DeltaRuntimeExit

        s_int = dl.lib.StateSaver(tuple_int, verbose=True)
        s_uint = dl.lib.StateSaver(tuple_uint, verbose=True)
        s_float = dl.lib.StateSaver(tuple_float, verbose=True)
        s_complex = dl.lib.StateSaver(tuple_complex, verbose=True)
        s_bool_char = dl.lib.StateSaver(tuple_bool_char, verbose=True)

        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()

            p.specify_by_node(testbench.call(
                s_int.save_and_ack(p.out_int),
                s_uint.save_and_ack(p.out_uint),
                s_float.save_and_ack(p.out_float),
                s_complex.save_and_ack(p.out_complex),
                s_bool_char.save_and_ack(p.out_bool_char)
            ))

        self.check_executes_graph(
            graph,
            """\
            saving (-128, -32768, -2147483648, -9223372036854775808)
            saving (127, 32767, 2147483647, 9223372036854775807)
            saving (0, 0, 0, 0)
            saving (255, 65535, 4294967295, 18446744073709551615)
            saving (1.0000001, 1.000000000000001)
            saving ((1.0000001+1.0000001j), (1.000000000000001+1.000000000000001j))
            saving (True, 'a')
            """
        )

    def test_compound(self):
        tuple_mix = dl.Tuple([
            dl.Int(dl.Size(8)),
            dl.UInt(dl.Size(16)),
            dl.Float(dl.Size(64)),
            dl.Complex(dl.Size(128)),
            dl.Bool(),
            dl.Str(dl.Size(10))
        ])
        array_float = dl.Array(dl.Float(dl.Size(64)), dl.Size(3))
        record_mix = dl.Record(RecATI)

        @dl.Interactive([("ack_tuple_mix", bool),
                         ("ack_array_float", bool),
                         ("ack_record_mix", bool)],
                        [("out_tuple_mix", tuple_mix),
                         ("out_array_float", array_float),
                         ("out_record_mix", record_mix)])
        def testbench(node: dl.PythonNode):
            node.send(out_tuple_mix=(-5, 1000, -100.5, (1.5+2.5j), False,
                                     '0123456789'))
            assert node.receive("ack_tuple_mix")

            node.send(out_array_float=[0.5, -0.25, 0.125])
            assert node.receive("ack_array_float")

            node.send(out_record_mix=RecATI([1, 2], (3.0, 4), 5))
            assert node.receive("ack_record_mix")

            raise DeltaRuntimeExit

        s_tuple_mix = dl.lib.StateSaver(tuple_mix, verbose=True)
        s_array_float = dl.lib.StateSaver(array_float, verbose=True)
        s_record_mix = dl.lib.StateSaver(record_mix, verbose=True)

        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()

            p.specify_by_node(testbench.call(
                s_tuple_mix.save_and_ack(p.out_tuple_mix),
                s_array_float.save_and_ack(p.out_array_float),
                s_record_mix.save_and_ack(p.out_record_mix)
            ))

        self.check_executes_graph(
            graph,
            """\
            saving (-5, 1000, -100.5, (1.5+2.5j), False, '0123456789')
            saving [0.5, -0.25, 0.125]
            saving RecATI(x=[1, 2], y=(3.0, 4), z=5)
            """
        )

    def test_union(self):
        union_mix = dl.Union([
            dl.Int(dl.Size(16)),
            dl.Bool(),
            dl.Str(dl.Size(10)),
            dl.Tuple([
                dl.Int(dl.Size(8)),
                dl.UInt(dl.Size(16)),
                dl.Float(dl.Size(64)),
                dl.Complex(dl.Size(128)),
                dl.Bool(),
                dl.Str(dl.Size(10))
            ]),
            dl.Record(RecATI)
        ])

        @dl.Interactive([("ack_union_mix", bool)],
                        [("out_union_mix", union_mix)])
        def testbench(node: dl.PythonNode):
            node.send(out_union_mix=5)
            assert node.receive("ack_union_mix")

            node.send(out_union_mix=False)
            assert node.receive("ack_union_mix")

            node.send(out_union_mix='abcd')
            assert node.receive("ack_union_mix")

            node.send(out_union_mix=(-5, 10, -1.5, (1.5+2.5j), False, 'hello'))
            assert node.receive("ack_union_mix")

            node.send(out_union_mix=RecATI([1, 2], (3.0, 4), 5))
            assert node.receive("ack_union_mix")

            raise DeltaRuntimeExit

        s_union_mix = dl.lib.StateSaver(union_mix, verbose=True)

        with dl.DeltaGraph() as graph:
            p = dl.placeholder_node_factory()

            p.specify_by_node(testbench.call(
                s_union_mix.save_and_ack(p.out_union_mix)
            ))

        self.check_executes_graph(
            graph,
            """\
            saving 5
            saving False
            saving abcd
            saving (-5, 10, -1.5, (1.5+2.5j), False, 'hello')
            saving RecATI(x=[1, 2], y=(3.0, 4), z=5)
            """
        )


if __name__ == "__main__":
    unittest.main()
