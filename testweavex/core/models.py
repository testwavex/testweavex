from __future__ import annotations

import hashlib
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


def generate_stable_id(*parts: str) -> str:
    """Generate a deterministic SHA-256 hash from parts.

    Uses the full 64-character hexdigest (no truncation).
    """
    key = "|".join(parts).encode("utf-8")
    return hashlib.sha256(key).hexdigest()


class TestStatus(str, Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    flaky = "flaky"


class TestType(str, Enum):
    smoke = "smoke"
    sanity = "sanity"
    happy_path = "happy_path"
    edge_cases = "edge_cases"
    data_driven = "data_driven"
    integration = "integration"
    system = "system"
    e2e = "e2e"
    accessibility = "accessibility"
    cross_browser = "cross_browser"


class GapStatus(str, Enum):
    open = "open"
    pending_review = "pending_review"
    closed = "closed"
    dismissed = "dismissed"
