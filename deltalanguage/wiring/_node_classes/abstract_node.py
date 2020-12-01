"""Module to describe the AbstractNode, ProxyNode and ForkedNode node classes.
"""

from abc import ABC, abstractmethod
from typing import Type

from .node_bodies import Body, Latency


class AbstractNode(ABC):
    """Abstract node class for :py:class:`DeltaGraph`.

    Used to derive :py:class:`ProxyNode` and :py:class:`RealNode`.

    ..
        Can't have more member data or methods at this level otherwise
        ProxyNodes would not work.
    """

    global_name_id = 0

    @classmethod
    def get_next_index(cls) -> int:
        """Fetch globally unique node names.

        Returns
        -------
        int
            a new node name that has not been used before
        """
        idx = AbstractNode.global_name_id
        AbstractNode.global_name_id += 1
        return idx

    @classmethod
    def reset_index(cls):
        """Reset the global node index.

        This is useful for tests where a fresh start is needed.
        """
        AbstractNode.global_name_id = 0

    @abstractmethod
    def add_out_port(self, port_destination, index=None):
        """Add out port.

        Parameters
        ----------
        port_destination : InPort
            The in-port that this out-port exports to.
        index : Optional[str]
            If this port is a fork then the type will be an indexed part
            of the output of the node.
        """
        pass

    @abstractmethod
    def add_in_port(self, port_name: str, in_type: Type):
        """Add in port.

        Parameters
        ----------
        port_name : str
            The name of the argument this port supplies.
        in_type : BaseDeltaType
            The type that is expected to be supplied for this port.
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of this node as str.

        Returns
        -------
        str
        """
        pass

    @property
    @abstractmethod
    def body(self) -> Body:
        """The body this node represents.

        Returns
        -------
        Body
        """
        pass

    @property
    @abstractmethod
    def latency(self) -> Latency:
        """The latency.

        Returns
        -------
        Latency
        """
        pass


class ProxyNode(AbstractNode):
    """Node class for a node that just refers to another node for all
    unspecified behaviours.

    Parameters
    ----------
    referee : AbstractNode
        Node that this proxy will act like. Defaults to ``None`` in which
        case any unhandled calls will throw exceptions.
    """

    def __init__(self, referee: AbstractNode = None):
        self.referee = referee

    def __getattr__(self, item):
        """Makes this node act like a proxy for the referee node.

        If this node defines some member behaviour it is fetched from here,
        otherwise it is fetched from the referee
        """
        return getattr(self.referee, item)

    def add_in_port(self, port_name: str, in_type: Type):
        """This function has been explicitly created as this is an abstract
        method calls add in-port on referee node.
        """
        self.referee.add_in_port(port_name, in_type)

    def add_out_port(self, port_destination, index=None):
        """This function has been explicitly created as this is an abstract
        method calls add out-port on referee node.
        """
        self.referee.add_out_port(port_destination, index)

    @property
    def name(self) -> str:
        return self.referee.name

    @property
    def body(self) -> Body:
        return self.referee.body

    @property
    def latency(self) -> Latency:
        return self.referee.latency


class ForkedNode(ProxyNode):
    """Node class to represent a pointer to a node that is forking its
    output to several other nodes.

    The main use of this class is to store the index at which this
    particular forked data can be found.

    Parameters
    ----------
    referee :
        The node that this node forks.
    index : str
        Index as string at which the data for this fork can be found
        on the referee nodes output.
    """

    def __init__(self, referee, index: str):
        super().__init__(referee)
        self.index = index

    def add_out_port(self, port_destination, index=None):
        """Add out port.

        Parameters
        ----------
        port_destination : InPort
            Where this out-port will go to, as InPort.
        index : Optional[str]
            Should always be none as we use this nodes stored index to create
            the port on the referee.
        """
        self.referee.add_out_port(port_destination, self.index)
