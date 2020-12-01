"""Port classes for bound ports between nodes.
Each node stores references to all of its in and out ports.
"""

from typing import NamedTuple, Union

import dill

from deltalanguage._utils import NamespacedName
from deltalanguage.data_types import BaseDeltaType, DOptional

from .abstract_node import AbstractNode


class InPort(
    NamedTuple(
        "InPort",
        [
            ("port_name", NamespacedName),
            ("port_type_", Union[BaseDeltaType, DOptional]),
            ("node", AbstractNode),
            ("in_port_size", int)
        ]
    )
):
    """Input port class.

    An instance of this class is created for every argument (input) of a node
    in :py:class:`DeltaGraph`.

    Attributes
    ----------
    port_name
        The name of the argument this port is supplying.
    port_type_
        The expected type of the value to be supplied.

        PRIVATE! Please use ``port_type`` and ``is_optional``.
    node
        The node this port is supplying to.
    in_port_size
        Limit for how many inputs this port can have enqueued.
        If a node tries to push more to this port's queue then it is blocked.


    .. TODO::
        ``InPort`` and ``OutPort`` can be implemented without ``NamedTuple``,
        thus ``port_type_`` hack won't be needed.
    """

    def __str__(self):
        return f"({self.port_name.n_index}, {self.port_type}, " +\
            f"{self.in_port_size}, {self.is_optional})"

    def __repr__(self):
        return f"({self.port_name}, {self.port_type}, " +\
            f"{self.in_port_size}, {self.is_optional})"

    @property
    def index(self):
        """Index of this port."""
        return self.port_name.n_index

    @property
    def node_name(self):
        """Node name of this port."""
        return self.port_name.domain

    @property
    def port_type(self):
        if isinstance(self.port_type_, DOptional):
            return self.port_type_.type
        else:
            return self.port_type_

    @property
    def is_optional(self):
        """Returns ``True`` if this port is created for an optional input."""
        return isinstance(self.port_type_, DOptional)

    def capnp(self, capnp_in_port):
        """Serialise this port in ``capnp`` structure.

        Parameters
        ----------
        capnp_in_port
            The ``capnp`` object of this in port.
        """
        capnp_in_port.name = self.port_name.n_index
        capnp_in_port.type = dill.dumps(self.port_type)
        capnp_in_port.optional = self.is_optional

    def capnp_wiring(self, nodes, capnp_wire):
        """Serialise the wire that this port connects to.

        Parameters
        ----------
        nodes
            List of nodes in capnp structure.
            Used to find required indexes.
        capnp_wire
            The capnp object of this wire.
        """
        for i, node in enumerate(nodes):
            if node.name == self.port_name.domain:
                capnp_wire.destNode = i
                for j, in_port in enumerate(node.inPorts):
                    if in_port.name == self.port_name.n_index:
                        capnp_wire.destInPort = j
                        break
                break
        capnp_wire.direct = (self.in_port_size > 0)


class OutPort(
    NamedTuple(
        "OutPort",
        [
            ("port_name", NamespacedName),
            ("port_type_", BaseDeltaType),
            ("destination", InPort),
            ("node", AbstractNode)
        ]
    )
):
    """Output port class.

    An instance of this class is created for every return (output) of a node
    in :py:class:`DeltaGraph`.

    Attributes
    ----------
    port_name
        The name of the part of the node output this port will export.
    port_type_
        The type of the part of the node output this port will export.
        This could be the type of the whole output.

        PRIVATE! Please use ``port_type``.
    destination
        Reference to the port that this node is exporting to.
    node
        The node this port is exporting from
    """

    def __str__(self):
        return f"({self.destination.port_name}, {self.port_type})"

    def __repr__(self):
        return f"({self.destination.port_name}, {self.port_name}, " +\
            f"{self.port_type})"

    @property
    def port_type(self):
        if isinstance(self.port_type_, DOptional):
            raise TypeError('OutPort cannot be optional')
        else:
            return self.port_type_

    @property
    def index(self):
        """Index of this port."""
        return self.port_name.n_index

    @property
    def dest_port_index(self):
        """Index of destination port."""
        return self.destination.index

    @property
    def dest_port_name(self):
        """Name of destination port (node name + index)."""
        return self.destination.port_name

    @property
    def dest_node_name(self):
        """Name of destination node."""
        return self.destination.node_name

    def capnp(self, capnp_out_port):
        """Serialise this port in ``capnp`` structure.

        Parameters
        ----------
        capnp_in_port
            The ``capnp`` object of this in port.
        """
        if self.port_name.n_index:
            capnp_out_port.name = self.port_name.n_index
        else:
            capnp_out_port.name = ""
        capnp_out_port.type = dill.dumps(self.port_type)

    def capnp_wiring(self, nodes, capnp_wire):
        """Serialise the wire that this port connects to.

        Parameters
        ----------
        nodes
            List of nodes in ``capnp`` structure.
            Used to find required indexes.
        capnp_wire
            The ``capnp`` object of this wire.
        """
        self.destination.capnp_wiring(nodes, capnp_wire)
