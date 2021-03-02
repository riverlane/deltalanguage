"""Special data types."""

from typing import (Any,
                    Dict,
                    Iterable,
                    List,
                    NamedTuple,
                    Tuple,
                    Type,
                    Union)

from deltalanguage._utils import NamespacedName
from ._exceptions import DeltaTypeError


class DSize:
    """Size of a Deltaflow type.

    Main usage is in :py:attr:`BaseDeltaType.size` and
    :py:attr:`DArray.length`.

    Parameters
    ----------
    size : Union[int, NamespacedName]
        It could be a definite size, or a
        placeholder for the actual size to be specified later.
    """

    def __init__(self, size: Union[int, NamespacedName]):
        self.is_placeholder = isinstance(size, NamespacedName)
        self.val = size

        if not self.is_placeholder and self.val < 0:
            raise ValueError("Only non-negative sizes for types are allowed.")

    def __repr__(self) -> str:
        if self.is_placeholder:
            return f"({self.val})"
        else:
            return f"{self.val}"

    def __eq__(self, other):
        if type(other) is DSize:
            return (self.is_placeholder == other.is_placeholder
                    and self.val == other.val)
        return False

    def __ge__(self, other):
        if type(other) is DSize:
            return (self.is_placeholder == other.is_placeholder
                    and self.val >= other.val)
        return False

    def __gt__(self, other):
        if self.is_placeholder or other.is_placeholder:
            raise ValueError("Please define DSize")
        return self.val > other.val

    def __hash__(self):
        return hash((self.is_placeholder, self.val))

    def __add__(self, other):
        if self.is_placeholder or other.is_placeholder:
            raise ValueError("Please define DSize")
        return DSize(self.val + other.val)

    def __iadd__(self, other):
        if self.is_placeholder or other.is_placeholder:
            raise ValueError("Please define DSize")
        self.val += other.val
        return self

    def __sub__(self, other):
        if self.is_placeholder or other.is_placeholder:
            raise ValueError("Please define DSize")
        return DSize(self.val - other.val)

    def __isub__(self, other):
        if self.is_placeholder or other.is_placeholder:
            raise ValueError("Please define DSize")

        self.val -= other.val

        if self.val < 0:
            raise ValueError("Only non-negative sizes for types are allowed.")

        return self

    def __mul__(self, other):
        if self.is_placeholder:
            raise ValueError("Please define DSize")

        if isinstance(other, int):
            return DSize(self.val * other)
        elif type(other) is DSize:
            return DSize(self.val * other.val)
        else:
            raise DeltaTypeError("Unsupported data type")

    def __rmul__(self, other):
        return self.__mul__(other)

    def __imul__(self, other):
        if self.is_placeholder:
            raise ValueError("Please define DSize")

        if isinstance(other, int):
            self.val *= other
        elif type(other) is DSize:
            self.val *= other.val
        else:
            raise DeltaTypeError("Unsupported data type")

        return self

    @property
    def in_bytes(self) -> int:
        if self.val % 8 == 0:
            return self.val//8
        else:
            raise ValueError(f'{self} bits need a fractional number of bytes')


class Void:
    """Used in cases if a node does not have and output channel.

    Examples
    --------
    In this case there is no need to even add a ``return`` statement.

    .. code-block:: python

        >>> import deltalanguage as dl

        >>> @dl.DeltaBlock()
        ... def foo(a: int) -> dl.Void:
        ...     print('Hello Quantum World!')

    If the node may or may not send a message
    you need to create a channel by specifying the output type:

    .. code-block:: python

        >>> @dl.DeltaBlock()
        ... def bar(a: int) -> int:
        ...     if a%2 == 0:
        ...         return a//2
        ...     else:
        ...         pass
    """
    pass
