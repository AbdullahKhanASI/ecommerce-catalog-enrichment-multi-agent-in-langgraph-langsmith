"""Workflow status event definitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict


@dataclass
class WorkflowEvent:
    step: str
    message: str
    payload: Dict[str, Any] | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def as_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "message": self.message,
            "payload": self.payload or {},
            "timestamp": self.timestamp.isoformat(),
        }
