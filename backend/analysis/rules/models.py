"""The types a rule, its result, and its session context are expressed as."""

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
    """What a rule costs — Stage A runs the CHEAP ones, Stage B the rest."""

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

    `score` None means the rule did not run; 0.0 means it ran and found
    nothing. The difference is kept as a NULL in `rules_analysis`.
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
    """One recorded event, narrower than the `events` row it is built from so
    the analysis layer does not depend on the storage schema."""

    timestamp: datetime
    host: str
    guard_action: str  # 'Allow' | 'Warn' | 'Block'
    risk_score: float


@dataclass
class SessionContext:
    """Session history for the contextual rules. The `current_event_*` fields
    describe the request being evaluated; `prior_events` is oldest first."""

    current_event_timestamp: Optional[datetime] = None
    current_event_host: str = ""
    prior_events: List[PriorEvent] = field(default_factory=list)
