"""An operator can decide which rules are allowed to hard block.

`is_hard_block` used to be read only from the catalogue, so the column in the
database was decoration: the dashboard displayed it and nothing consulted it.
These tests pin the behaviour that makes the setting real, and the two ways it
could quietly stop working — the catalogue overwriting the operator's choice on
the next request, and the flag on the recorded result disagreeing with the flag
that actually short-circuited the loop.
"""

from unittest.mock import patch

from backend.analysis.stages.stage_a import StageAEvaluator
from backend.feature_extraction.feature_extractor import FeatureExtractor

_BLACKLIST = "backend.analysis.stages.stage_a.blacklist.blacklist_cache.is_listed"
_HTML = "<html><body><p>hello</p></body></html>"


def _evaluate(url: str, hard_block_rules=None):
    features = FeatureExtractor().extract(
        url=url, method="GET", headers={"content-type": "text/html"}, body=_HTML,
    )
    return StageAEvaluator().evaluate(features, hard_block_rules=hard_block_rules)


class TestHardBlockOverride:
    def test_catalogue_decides_when_no_override_is_supplied(self):
        with patch(_BLACKLIST, return_value=(True, "listed")):
            result = _evaluate("https://listed.example.com/")
        assert result.hard_block_triggered is True

    def test_operator_can_stop_a_rule_hard_blocking(self):
        with patch(_BLACKLIST, return_value=(True, "listed")):
            result = _evaluate("https://listed.example.com/",
                               hard_block_rules={"domain_blacklist": False})
        # The page may still score badly; what must change is that no single
        # rule short-circuited the evaluation.
        assert result.hard_block_triggered is False

    def test_operator_can_promote_a_rule_to_hard_blocking(self):
        """A high-abuse TLD normally contributes a score; here it blocks alone."""
        with patch(_BLACKLIST, return_value=(False, "not listed")):
            before = _evaluate("https://cheap-domain.shop/")
            after = _evaluate("https://cheap-domain.shop/",
                              hard_block_rules={"suspicious_tld": True})

        assert before.hard_block_triggered is False
        assert after.hard_block_triggered is True
        assert after.risk_score == 1.0

    def test_a_rule_not_named_in_the_override_keeps_its_catalogue_value(self):
        with patch(_BLACKLIST, return_value=(True, "listed")):
            result = _evaluate("https://listed.example.com/",
                               hard_block_rules={"suspicious_tld": True})
        assert result.hard_block_triggered is True

    def test_the_recorded_flag_matches_what_actually_happened(self):
        """Every result carries the flag that was applied, not the catalogue's.

        The dashboard reads this. When the two disagreed it reported pages as
        hard-blocked on the strength of a rule's capability rather than on
        anything the rule did.
        """
        with patch(_BLACKLIST, return_value=(False, "not listed")):
            result = _evaluate("https://cheap-domain.shop/",
                               hard_block_rules={"suspicious_tld": True,
                                                 "domain_blacklist": False})

        by_id = {r.rule_id: r for r in result.rule_results}
        assert by_id["suspicious_tld"].hard_block is True
        assert by_id["domain_blacklist"].hard_block is False
