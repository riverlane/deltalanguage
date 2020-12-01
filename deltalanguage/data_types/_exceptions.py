"""Deltaflow specific exceptions."""


class DeltaTypeError(Exception):
    """Raised on multiple occasions:

      - if Deltaflow data type is mismanaged in general
      - if a connection of
        :py:class:`DeltaGraph<deltalanguage.wiring.DeltaGraph>`
        has a mismatch at the receiving and sending ends
    """
    pass


class DeltaIOError(Exception):
    """Raised when :py:class:`DeltaGraph<deltalanguage.wiring.DeltaGraph>` has
    a an error in connectivity.
    """
    pass


class NoMessage(Exception):
    """Used in cases if a node does not have and output channel.

    Examples
    --------
    In this case there is no need to even add a ``return`` statement.

    .. code-block:: python

        @DeltaBlock()
        def foo(a: int) -> NoMessage:
            print('Hello Quantum World!')

    If the node may or may not send a message
    you need to create a channel by specifying the output type:

    .. code-block:: python

        @DeltaBlock()
        def bar(a: int) -> int:
            if a%2 == 0:
                return a//2
            else:
                pass
    """
    pass
