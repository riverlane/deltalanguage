"""Port classes for bound ports between nodes.
Each node stores references to all of its in and out ports.
"""

from typing import NamedTuple, Union

import dill

from deltalanguage.data_types import BaseDeltaType, Optional

from .abstract_node import AbstractNode


class InPort(
    NamedTuple(
        "InPort",
        [
            ("index", str),
            ("port_type_", Union[BaseDeltaType, Optional]),
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
    index
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
        ret = f"{self.index}, {self.port_type}"
        if self.is_optional:
            ret += ", optional"

        return ret

    def __repr__(self):
        return f"({self.name}, {self.port_type}, " +\
            f"{self.in_port_size}, {self.is_optional})"

    @property
    def name(self) -> str:
        """Unique port name as string, formed from the node name and port index.
        """
        return f"{self.node.full_name}.{self.index}"

    @property
    def node_name(self):
        """Node name of this port."""
        return self.node.full_name

    @property
    def port_type(self):
        if isinstance(self.port_type_, Optional):
            return self.port_type_.type
        else:
            return self.port_type_

    @property
    def is_optional(self):
        """Returns ``True`` if this port is created for an optional input."""
        return isinstance(self.port_type_, Optional)

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism as component of .df file
        """
        if not isinstance(other, InPort):
            return False

        if self.index != other.index:
            return False
        
        if self.port_type != other.port_type:
            return False

        if self.is_optional != other.is_optional:
            return False

        if self.in_port_size != other.in_port_size:
            return False

        if self.node != other.node:
            return False

        return True

    def capnp(self, capnp_in_port):
        """Serialise this port in ``capnp`` structure.

        Parameters
        ----------
        capnp_in_port
            The ``capnp`` object of this in port.
        """
        capnp_in_port.name = self.index
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
            if node.name == self.node.full_name:
                capnp_wire.destNode = i
                for j, in_port in enumerate(node.inPorts):
                    if in_port.name == self.index:
                        capnp_wire.destInPort = j
                        break
                break
        capnp_wire.direct = (self.in_port_size > 0)


class OutPort(
    NamedTuple(
        "OutPort",
        [
            ("index", str),
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
    index
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
        ret = f"{self.index}, {self.port_type} -> {self.destination.name}"
        return ret

    def __repr__(self):
        return f"({self.destination.name}, {self.name}, " +\
            f"{self.port_type})"

    @property
    def port_type(self):
        if isinstance(self.port_type_, Optional):
            raise TypeError('OutPort cannot be optional')
        else:
            return self.port_type_

    @property
    def dest_port_index(self):
        """Index of destination port."""
        return self.destination.index

    @property
    def dest_port_name(self):
        """Name of destination port (node name + index)."""
        return self.destination.name

    @property
    def name(self) -> str:
        """Unique port name as string, formed from node name and port index
        """
        return f"{self.node.full_name}.{self.index}"

    @property
    def dest_node_name(self):
        """Name of destination node."""
        return self.destination.node_name

    def __eq__(self, other) -> bool:
        """Equality, up to isomorphism as component of .df file
        """
        if not isinstance(other, OutPort):
            return False

        if self.index != other.index:
            return False
        
        if self.port_type != other.port_type:
            return False

        if self.destination != other.destination:
            return False

        if self.node != other.node:
            return False

        return True


    def capnp(self, capnp_out_port):
        """Serialise this port in ``capnp`` structure.

        Parameters
        ----------
        capnp_in_port
            The ``capnp`` object of this in port.
        """
        capnp_out_port.name = self.index
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
