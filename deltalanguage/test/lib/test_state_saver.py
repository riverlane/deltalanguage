import tempfile
import unittest

from deltalanguage.lib import StateSaver
from deltalanguage.wiring import DeltaGraph, DeltaBlock
from deltalanguage.runtime import DeltaPySimulator, DeltaRuntimeExit
from deltalanguage.data_types import DRecord, DUnion, DArray, DSize, DTuple
import attr


@attr.s(slots=True)
class SimpleRecord:

    x: int = attr.ib()
    y: bool = attr.ib()


@attr.s(slots=True)
class ComplexRecord:

    x: complex = attr.ib()


@attr.s(slots=True)
class ArrayRecord:

    x: DArray([ComplexRecord], length=DSize(1)) = attr.ib()


@attr.s(slots=True)
class NestedRecord:

    x: int = attr.ib()
    y: SimpleRecord = attr.ib()


class TestStateSaver(unittest.TestCase):
    def test_can_save_to_tempfile(self):
        """Test StateSaver can save to a file."""
        st = [(k, k**2) for k in range(5)]
        # Note the conversion to a list as the json format doesn't care
        # for tuples.
        st_expected = "\n".join(repr(list(x)) for x in st)

        items = [
            ((int, int), (42, 100), "[42, 100]"),
            ((int, int), st, st_expected),
            (str, "Hello", '"Hello"'),
            (bool, True, "true"),
            (float, 3.91, "3.91"),
            (DTuple([int, int]), (1, 2), "[1, 2]"),
            (DUnion([int, float]), 90, "90"),
            (DUnion([int, float]), 90.0, "90.0"),
            (complex, 1j, '{"real": 0.0, "imaginary": 1.0}'),
            (SimpleRecord, SimpleRecord(x=1, y=True), '{"x": 1, "y": true}'),
            (
                ComplexRecord,
                ComplexRecord(x=1 + 2j),
                '{"x": {"real": 1.0, "imaginary": 2.0}}'
            ),
            (
                NestedRecord,
                NestedRecord(x=3, y=SimpleRecord(x=1, y=True)),
                '{"x": 3, "y": {"x": 1, "y": true}}'
            ),
            (
                ArrayRecord,
                ArrayRecord(x=[ComplexRecord(x=-1+4j)]),
                '{"x": [{"x": {"real": -1.0, "imaginary": 4.0}}]}'
            )
        ]

        for i, item in enumerate(items):
            t, data, expected = item
            with self.subTest(i=i):
                with tempfile.NamedTemporaryFile(mode="w+") as f:
                    s = StateSaver(t, verbose=True, filename=f.name)

                    @DeltaBlock(allow_const=False)
                    def save_things_node() -> object:
                        # If it's a list, save them independently, otherwise
                        # it's just one thing.
                        if type(data) == list:
                            for d in data:
                                s.save(d)
                        else:
                            s.save(data)
                        raise DeltaRuntimeExit

                    with DeltaGraph() as graph:
                        save_things_node()

                    rt = DeltaPySimulator(graph)
                    rt.run()

                    f.seek(0)

                    contents = f.read()
                    self.assertEqual(contents, f"{expected}\n")
