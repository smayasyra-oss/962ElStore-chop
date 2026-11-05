"""إعداد السجلات مع إخفاء الأسرار تلقائياً (التوكن، رابط القاعدة، PIN)."""
from __future__ import annotations

import logging
import re

_PATTERNS = [
    (re.compile(r"\d{6,12}:[A-Za-z0-9_-]{30,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"(postgres(?:ql)?://[^:/\s@]+:)([^@\s]+)(@)"), r"\1[REDACTED]\3"),
    (re.compile(r"(?i)(pin|password|passwd|secret|token)(\s*[=:]\s*)\S+"), r"\1\2[REDACTED]"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record))


def setup_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(
        RedactingFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level, logging.INFO))
    # مكتبة httpx تطبع روابط فيها التوكن، نخفض مستواها
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
