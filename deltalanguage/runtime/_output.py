from __future__ import annotations
from typing import TYPE_CHECKING, List, Tuple, Union

import capnp

# use the import magic from capnp to get the schema
import deltalanguage.data_types.dotdf_capnp \
    as dotdf_capnp  # pylint: disable=E0401, disable=E0611

if TYPE_CHECKING:
    from deltalanguage.wiring import DeltaGraph


def serialize_graph(
    graph: DeltaGraph,
    name: str = None,
    files: List[str] = []
) -> Tuple[bytes, capnp.lib.capnp._DynamicStructBuilder]:
    """Converts a complete representation of the Deltaflow program stored as
    a :py:class:`DeltaGraph` to bytecode.

    Parameters
    ----------
    graph : DeltaGraph
        Deltaflow graph.
    name : str
        Name of the program. If no name is provided then this is the same
        as the name of the graph.
    files : List[str]
        Additional files required for the program to run, such as user-defined
        packages or data.

    Returns
    -------
    bytes
        Bytestring formatted according to the Deltaflow schema.
    capnp.lib.capnp._DynamicStructBuilder
        Data schema.
    """
    schema = dotdf_capnp.Program.new_message()
    if name:
        schema.name = name
    elif graph.name:
        schema.name = graph.name

    capnp_files = schema.init("files", len(files))
    for capnp_file, prog_file in zip(capnp_files, files):
        capnp_file.name = prog_file
        with open(prog_file, "rb") as file_content:
            capnp_file.content = file_content.read()

    graph.do_automatic_splitting()

    bodies = schema.init_resizable_list("bodies")
    nodes = schema.init("nodes", len(graph.nodes))
    wiring = schema.init_resizable_list("graph")

    for graph_node, capnp_node in zip(graph.nodes, nodes):
        graph_node.capnp(capnp_node, bodies)

    for graph_node in graph.nodes:
        graph_node.capnp_wiring(nodes, wiring)

    # resizable lists initialize only here
    bodies.finish()
    wiring.finish()

    return schema.to_bytes(), schema


def deserialize_graph(
    data: bytes
) -> Union[capnp._DynamicStructReader, capnp._DynamicStructBuilder]:
    """Converts bytecode to a complete graph representation of the Deltaflow
    program.

    Parameters
    ----------
    data : bytes
        Bytestring formatted according to the Deltaflow schema.

    Returns
    -------
    Union[capnp._DynamicStructReader, capnp._DynamicStructBuilder]
        Deltaflow graph.
    """
    return dotdf_capnp.Program.from_bytes(data)
