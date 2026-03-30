from backend_api_test_base import BackendApiTestCase


class RulesAnalysisTestCase(BackendApiTestCase):
    def test_rules_and_rule_analysis_endpoints(self):
        session_id = self.create_session().get_json()["session_id"]
        event_id = self.create_event(
            session_id,
            guard_action="Block",
            risk_score=0.95,
        ).get_json()["event_id"]

        create_rule = self.create_rule(rule_code="RISKY")
        self.assertEqual(create_rule.status_code, 201)
        self.assertEqual(create_rule.get_json()["rule"]["rule_code"], "RISKY")

        duplicate_rule = self.create_rule(rule_code="RISKY")
        self.assertEqual(duplicate_rule.status_code, 409)
        self.assertEqual(duplicate_rule.get_json()["error"], "rule_code already exists")

        analysis = self.client.post(
            "/rules-analysis",
            json={
                "event_id": event_id,
                "rule_code": "RISKY",
                "rule_score": 0.91,
                "details": "Matched suspicious pattern",
            },
        )
        self.assertEqual(analysis.status_code, 201)
        analysis_id = analysis.get_json()["analysis_id"]

        by_event = self.client.get(f"/events/{event_id}/rules-analysis")
        self.assertEqual(by_event.status_code, 200)
        self.assertEqual(len(by_event.get_json()), 1)
        self.assertEqual(by_event.get_json()[0]["analysis_id"], analysis_id)

        by_rule = self.client.get("/rules-analysis", query_string={"rule_code": "RISKY", "limit": "5"})
        self.assertEqual(by_rule.status_code, 200)
        self.assertEqual(len(by_rule.get_json()), 1)
        self.assertEqual(by_rule.get_json()[0]["event_id"], event_id)

    def test_rule_analysis_empty_and_missing_references(self):
        create_rule = self.create_rule(rule_code="EMPTY")
        self.assertEqual(create_rule.status_code, 201)

        empty_analysis = self.client.get("/rules-analysis", query_string={"rule_code": "EMPTY", "limit": "5"})
        self.assertEqual(empty_analysis.status_code, 200)
        self.assertEqual(empty_analysis.get_json(), [])

        missing_event = self.client.get("/events/999/rules-analysis")
        self.assertEqual(missing_event.status_code, 404)

        missing_reference = self.client.post(
            "/rules-analysis",
            json={
                "event_id": 999,
                "rule_code": "EMPTY",
                "rule_score": 0.5,
                "details": "No event",
            },
        )
        self.assertEqual(missing_reference.status_code, 404)

    def test_rule_validation_errors(self):
        negative_weight = self.create_rule(weight=-0.1)
        self.assertEqual(negative_weight.status_code, 400)
        self.assertEqual(negative_weight.get_json()["error"], "Invalid weight")

        session_id = self.create_session().get_json()["session_id"]
        event_id = self.create_event(session_id).get_json()["event_id"]
        self.create_rule(rule_code="TRIMMED")

        invalid_rule_score = self.client.post(
            "/rules-analysis",
            json={
                "event_id": event_id,
                "rule_code": "TRIMMED",
                "rule_score": 1.5,
                "details": "Too high",
            },
        )
        self.assertEqual(invalid_rule_score.status_code, 400)
        self.assertEqual(invalid_rule_score.get_json()["error"], "Invalid rule_score")

        trimmed_query = self.client.get("/rules-analysis", query_string={"rule_code": "  TRIMMED  ", "limit": "5"})
        self.assertEqual(trimmed_query.status_code, 200)
        self.assertEqual(trimmed_query.get_json(), [])
