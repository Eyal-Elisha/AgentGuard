"""The vocabulary the rule engine is written in.

Nothing here evaluates anything: these are the types that a rule, its result,
and the session it ran against are expressed as. Both stages, the storage
layer and the proxy all speak in terms of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class RuleType(str, Enum):
    DETERMINISTIC = "deterministic"
    CONTEXTUAL = "contextual"
    SEMANTIC = "semantic"


class ComputeClass(str, Enum):
    """What a rule costs to run — the basis for the two-stage split.

    Stage A runs every CHEAP rule; the EXPENSIVE ones are held back for Stage B
    and only run when Stage A leaves the verdict undecided.
    """

    CHEAP = "cheap"
    EXPENSIVE = "expensive"


class Decision(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class RuleDefinition:
    """Static metadata describing a single rule."""

    rule_id: str
    description: str
    rule_type: RuleType
    compute_class: ComputeClass
    weight: float
    hard_block: bool


@dataclass
class RuleResult:
    """What one rule concluded about one request.

    A `score` of None means the rule did not run — because it was disabled, its
    preconditions were not met, or a hard block short-circuited the stage. That
    is distinct from a score of 0.0, which means the rule ran and found
    nothing, and the difference is preserved all the way into the
    `rules_analysis` table as a NULL.
    """

    rule_id: str
    rule_type: RuleType
    score: Optional[float]
    hard_block: bool
    explanation: str
    triggered: bool


@dataclass
class EvaluationResult:
    """The outcome of a stage, or of the whole pipeline."""

    decision: Decision
    risk_score: float
    rule_results: List[RuleResult]
    hard_block_triggered: bool = False
    stage_b_required: bool = False


@dataclass
class PriorEvent:
    """One event already recorded in the current session.

    Deliberately narrower than the `events` row it is built from, so the
    analysis layer does not depend on the storage schema.
    """

    timestamp: datetime
    host: str
    guard_action: str  # 'Allow' | 'Warn' | 'Block'
    risk_score: float


@dataclass
class SessionContext:
    """The session history that contextual rules reason over.

    `current_event_timestamp` and `current_event_host` describe the request
    being evaluated right now, which is not persisted yet. `prior_events` holds
    the events already stored for the same session, oldest first, none of them
    later than the current one.
    """

    current_event_timestamp: Optional[datetime] = None
    current_event_host: str = ""
    prior_events: List[PriorEvent] = field(default_factory=list)
