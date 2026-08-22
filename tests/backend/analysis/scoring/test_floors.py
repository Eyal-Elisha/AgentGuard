"""Decision floors: a rule forcing a minimum decision on its own."""

from __future__ import annotations

import pytest

from backend.analysis.rules import Decision, RuleResult, RuleType
from backend.analysis.scoring.floors import apply_decision_floors, applicable_floors


def _result(rule_id: str, score: float | None, triggered: bool = True) -> RuleResult:
    return RuleResult(
        rule_id=rule_id,
        rule_type=RuleType.SEMANTIC,
        score=score,
        hard_block=False,
        explanation="test",
        triggered=triggered,
    )


class TestPromptInjectionFloor:
    def test_raises_allow_to_warn(self):
        """The case this exists for: the combiner says Allow, the injection
        rule is confident, and the page must not reach the agent silently."""
        results = [_result("prompt_injection", 0.94)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.WARN

    def test_does_not_lower_a_block(self):
        results = [_result("prompt_injection", 0.94)]
        assert apply_decision_floors(Decision.BLOCK, results) is Decision.BLOCK

    def test_below_threshold_does_nothing(self):
        """0.92 fires the rule (trigger 0.85) but is below the floor, which is
        deliberately stricter: contributing evidence and overriding the scorer
        are different acts."""
        results = [_result("prompt_injection", 0.92)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.ALLOW

    def test_exactly_at_threshold_applies(self):
        results = [_result("prompt_injection", 0.93)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.WARN

    def test_demonstration_payload_is_caught(self):
        """demo_pages/injection.html scores 0.9356. If this regresses, the
        canonical prompt-injection demonstration silently stops working."""
        results = [_result("prompt_injection", 0.9356)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.WARN

    def test_untriggered_rule_is_ignored(self):
        """A score above the threshold on a rule that did not fire (for
        instance because it was disabled) must not force a decision."""
        results = [_result("prompt_injection", 0.99, triggered=False)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.ALLOW

    def test_none_score_is_ignored(self):
        results = [_result("prompt_injection", None)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.ALLOW


class TestUnfloored:
    def test_rule_without_a_floor_changes_nothing(self):
        results = [_result("phishing_language", 0.99)]
        assert apply_decision_floors(Decision.ALLOW, results) is Decision.ALLOW

    def test_no_results_changes_nothing(self):
        assert apply_decision_floors(Decision.ALLOW, []) is Decision.ALLOW


class TestApplicableFloors:
    def test_reports_the_rule_that_demanded_the_floor(self):
        results = [_result("phishing_language", 0.99), _result("prompt_injection", 0.95)]
        assert applicable_floors(results) == [("prompt_injection", Decision.WARN)]

    @pytest.mark.parametrize("decision", list(Decision))
    def test_never_lowers_any_decision(self, decision):
        """Whatever the scorer decided, a floor may raise it but never relax it."""
        severity = {Decision.ALLOW: 0, Decision.WARN: 1, Decision.BLOCK: 2}
        out = apply_decision_floors(decision, [_result("prompt_injection", 0.94)])
        assert severity[out] >= severity[decision]
