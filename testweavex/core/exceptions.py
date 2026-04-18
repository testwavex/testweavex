class TestWeaveXError(Exception):
    """Base exception for all TestWeaveX errors."""


class ConfigError(TestWeaveXError):
    """Raised when testweavex.config.yaml is missing, unreadable, or invalid."""


class StorageError(TestWeaveXError):
    """Raised when a database read or write operation fails."""


class RecordNotFound(StorageError):
    """Raised when a requested record does not exist in storage."""


class LLMOutputError(TestWeaveXError):
    """Raised when the LLM returns output that cannot be parsed or validated.
    Active from Phase 2 onwards.
    """


class SkillNotFoundError(TestWeaveXError):
    """Raised when a requested skill YAML file does not exist.
    Active from Phase 2 onwards.
    """


class GenerationError(TestWeaveXError):
    """Raised when the generation pipeline fails after exhausting retries.
    Active from Phase 3 onwards.
    """


class TCMConnectorError(TestWeaveXError):
    """Raised when communication with an external TCM (TestRail, Xray) fails.
    Active from Phase 7 onwards.
    """
