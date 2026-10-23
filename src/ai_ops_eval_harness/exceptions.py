"""Core exceptions for pipeline assertions and statistical circuit breakers."""

class EvalAssertionError(Exception):
    """Raised when a declarative evaluation assertion fails."""
    pass

class DataStarvationError(EvalAssertionError):
    """Raised when data pipeline drops rows unexpectedly or encounters 0% yield."""
    pass

class FinancialAnomalyError(EvalAssertionError):
    """Raised when financial baseline or metric variance violates statistical bounds."""
    pass
