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
