"""Stdlib logging adapter that preserves key=value call-site ergonomics."""

import logging
from typing import Any, MutableMapping


_LOG_KWARGS = frozenset(("exc_info", "stack_info", "stacklevel"))


class _KeywordAdapter(logging.LoggerAdapter):
    """Wraps a stdlib Logger, converting keyword call-site arguments into extra fields."""

    def process(self, msg: str, kwargs: MutableMapping[str, Any]):
        extra = dict(self.extra)
        log_kwargs: dict[str, Any] = {}

        for key in list(kwargs):
            if key in _LOG_KWARGS:
                log_kwargs[key] = kwargs[key]
            elif key == "extra":
                extra.update(kwargs[key])
            else:
                extra[key] = kwargs[key]

        log_kwargs["extra"] = extra
        return msg, log_kwargs

    def bind(self, **context: Any) -> "_KeywordAdapter":
        """Return a new adapter with additional fixed context fields."""
        return _KeywordAdapter(self.logger, {**self.extra, **context})


def get_logger(name: str) -> _KeywordAdapter:
    """Return a keyword-aware logger adapter for the given module name."""
    return _KeywordAdapter(logging.getLogger(name), {})
