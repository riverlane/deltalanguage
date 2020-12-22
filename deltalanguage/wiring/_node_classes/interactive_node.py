from __future__ import annotations
import sys
from typing import TYPE_CHECKING, Callable

from deltalanguage.data_types import NoMessage

from .node_bodies import PyInteractiveBody
from .real_nodes import PythonNode, as_node

if TYPE_CHECKING:
    from deltalanguage.wiring import DeltaGraph, InteractiveProcess, Latency


class PyInteractiveNode(PythonNode):
    """Python Interactive Node defined via :py:class:`Interactive`.

    Parameters
    ----------
    graph : DeltaGraph
        Graph the node will be part of
    proc : InteractiveProcess
        Constructed process with the proc function and I/O types.
    latency : Latency
        The estimated latency for running the body.
    kwargs
        Nodes to make in-ports for or Python objects to be made into
        :py:class:`PyConstNode`.
    """

    def __init__(self,
                 graph: DeltaGraph,
                 proc: InteractiveProcess,
                 latency: Latency = None,
                 **kwargs):
        super().__init__(graph,
                         PyInteractiveBody(proc.proc),
                         return_type=proc.return_type,
                         name=proc.name,
                         latency=latency,
                         lvl=proc.lvl)
        kw_in_nodes = {name: as_node(arg, graph)
                       for (name, arg) in kwargs.items()}
        self._create_upstream_ports(
            proc.arg_types, kw_in_nodes, proc.in_port_size)

    def thread_worker(self, runtime):
        """Run an Interactive Node, which amounts to handing over control
        to a user-defined function in the body.

        .. warning::
            Overwrites :meth:`PythonNode.thread_worker`.
        """
        self.set_communications(runtime)

        self.log.debug(f"Running... {self}")
        try:
            self.body.eval(self)
        except NoMessage:
            self.log.error("Interactive nodes cannot raise NoMessage")
            raise
        except:
            raise

    def capnp(self, capnp_node, capnp_bodies):
        """Generate capnp form of this node.
        Overloads PythonNode implementation so that Interactive bodies can be
        specified differently as they take different inputs.

        Parameters
        ----------
        capnp_node
            The capnp object of this node.
        capnp_bodies
            List of bodies so we can check if a body is already serialised.
        """
        capnp_node.name = self.name

        dill_impl = self.get_serialised_body()

        for i, body in enumerate(capnp_bodies):
            if body.which() == 'interactive':
                if body.interactive.dillImpl == dill_impl:
                    capnp_node.body = i
                    break

        else:
            body = capnp_bodies.add()
            body.init('interactive')
            body.interactive.dillImpl = dill_impl
            capnp_node.body = len(capnp_bodies)-1

        # 2. save I/O ports
        self.capnp_ports(capnp_node)


# This node is used by the Interactive decorator
InteractiveFuncType = Callable[[PyInteractiveNode], None]
