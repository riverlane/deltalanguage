from typing import List

from deltalanguage.data_types import make_forked_return
from deltalanguage._utils import QueueMessage

from .port_classes import InPort
from .real_nodes import RealNode, PythonNode
from .node_bodies import Latency, PySplitterBody


class SplitterNode(RealNode):
    """Node class for splitter nodes.

    These are expected to take a single input and copy this value to several
    locations.

    Parameters
    ----------
    graph : DeltaGraph
        Graph this node is a part of.
    body : Body
        Reference to a body that will split the data as required.
    in_type : BaseDeltaType
        The type of the input for this node.
    out_type : BaseDeltaType
        The type of the output for this node.
    destinations : List[InPort]
        As a list of InPorts, these are the destinations this node will
        output to.
    
    .. deprecated:: 0.5
        Use ``DeltaGraph.do_automatic_splitting``.
    """

    def __init__(self,
                 graph,
                 body,
                 in_type,
                 out_type,
                 destinations: List[InPort]):
        super().__init__(graph, body,
                         out_type,
                         name="splitter",
                         latency=Latency(clocks=0))

        # Add this node's single in_port
        self.add_in_port("in", in_type)

        # Add all of this node's out ports
        for i, dest in enumerate(destinations):
            self.add_out_port(dest, 'out' + str(i))

    @property
    def get_in_port(self):
        """Iterate over in ports.

        Returns
        -------
        InPort
        """
        return next(iter(self.in_ports.values()))


class PySplitterNode(SplitterNode, PythonNode):
    """Node class for splitter nodes in python.

    Makes a node that takes a single input and slits it to multiple
    defined destination nodes.

    Parameters
    ----------
    graph : DeltaGraph
        Graph this node is a part of.
    split_val_type : BaseDeltaType
        The type of the input expected and thus the individual outputs
        given.
    destinations : List[InPort]
        As a list of InPorts, these are the destinations this node will
        output to.


    .. deprecated:: 0.5
        Use ``DeltaGraph.do_automatic_splitting``.
    """

    def __init__(self, graph, split_val_type, destinations: List[InPort]):
        num_dests = len(destinations)

        # Create the split return type, this is a named tuple containing
        # num_dests references to the same type
        return_fields = {'out' + str(i): split_val_type
                         for i in range(0, num_dests)}
        split_out_typeT, split_out_type = make_forked_return(return_fields)

        body = PySplitterBody(num_dests, split_out_type)

        super().__init__(graph,
                         body,
                         split_val_type,
                         split_out_typeT,
                         destinations)

        self.in_queue = None
        self.out_queues = None

    def assign_runtime(self, runtime):
        in_queues = runtime.in_queues[self.name]
        assert len(in_queues) == 1
        self.in_queue = next(iter(in_queues.values()))
        self.out_queues = runtime.out_queues[self.name]

    def split(self):
        val = self.in_queue.get_or_none()
        if val.msg is not None:
            self.msg_log.add_message(self.name, "val", val)
            split = self.body.eval(val.msg)
            for out_q in self.out_queues.values():
                # we assume network operations, like splitter nodes, don't
                # update the logical time (as they are not user logic)
                out_q.put(QueueMessage(split, clk=val.clk))
