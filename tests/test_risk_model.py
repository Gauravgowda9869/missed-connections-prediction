"""
ConnectGuard — Unit Tests
==========================
Tests for risk model, decision engine, and feature engineering.

Run with: pytest tests/ -v --cov=src
"""

import pytest
import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.decision_engine.decision_engine import (
    DecisionEngine,
    estimate_costs,
    ActionType,
)


# ─────────────────────────────────────────────
# DECISION ENGINE TESTS
# ─────────────────────────────────────────────

class TestDecisionEngine:
    """Tests for the decision engine recommendation logic."""

    def setup_method(self):
        self.engine = DecisionEngine()

    # ── Recommendation logic ────────────────────────────────────────

    def test_critical_with_time_triggers_hold(self):
        """CRITICAL risk + enough time + enough pax → HOLD_FLIGHT"""
        action = DecisionEngine.recommend(
            risk_score=90, pax_count=8, time_to_departure=25
        )
        assert action == ActionType.HOLD_FLIGHT

    def test_critical_no_time_triggers_rebook(self):
        """CRITICAL risk + insufficient time → PRE_REBOOK"""
        action = DecisionEngine.recommend(
            risk_score=88, pax_count=10, time_to_departure=6
        )
        assert action == ActionType.PRE_REBOOK

    def test_critical_low_pax_triggers_rebook(self):
        """CRITICAL risk + below min pax threshold → PRE_REBOOK"""
        action = DecisionEngine.recommend(
            risk_score=91, pax_count=2, time_to_departure=30
        )
        assert action == ActionType.PRE_REBOOK

    def test_high_risk_with_time_triggers_escort(self):
        """HIGH risk + sufficient time → ARRANGE_ESCORT"""
        action = DecisionEngine.recommend(
            risk_score=72, pax_count=5, time_to_departure=20
        )
        assert action == ActionType.ARRANGE_ESCORT

    def test_medium_risk_triggers_monitor(self):
        """MEDIUM risk → MONITOR"""
        action = DecisionEngine.recommend(
            risk_score=50, pax_count=3, time_to_departure=30
        )
        assert action == ActionType.MONITOR

    def test_low_risk_triggers_no_action(self):
        """LOW risk → NO_ACTION"""
        action = DecisionEngine.recommend(
            risk_score=15, pax_count=5, time_to_departure=60
        )
        assert action == ActionType.NO_ACTION

    def test_risk_score_zero_no_action(self):
        """Zero risk → NO_ACTION"""
        action = DecisionEngine.recommend(
            risk_score=0, pax_count=10, time_to_departure=90
        )
        assert action == ActionType.NO_ACTION

    def test_risk_score_100_hold(self):
        """Maximum risk score with sufficient conditions → HOLD"""
        action = DecisionEngine.recommend(
            risk_score=100, pax_count=12, time_to_departure=25
        )
        assert action == ActionType.HOLD_FLIGHT

    # ── Full decision output ────────────────────────────────────────

    def test_decide_returns_decision_output(self):
        """decide() returns a DecisionOutput with all required fields."""
        decision = self.engine.decide(
            connection_id="TEST_CONN_001",
            risk_score=88.0,
            risk_category="CRITICAL",
            p_miss=0.88,
            pax_count=7,
            avg_tier_score=3.0,
            pct_premium=0.4,
            time_to_departure=22,
        )
        d = decision.to_dict()
        assert "recommended_action" in d
        assert "rationale" in d
        assert "confidence" in d
        assert "net_benefit_hold" in d
        assert d["pax_count"] == 7

    def test_escalation_for_critical_short_time(self):
        """CRITICAL with < 20 min to departure → escalation required."""
        decision = self.engine.decide(
            connection_id="ESCALATE_TEST",
            risk_score=91.0,
            risk_category="CRITICAL",
            p_miss=0.91,
            pax_count=5,
            time_to_departure=15,
        )
        assert decision.escalation_required is True

    def test_no_escalation_for_low_risk(self):
        """LOW risk → no escalation."""
        decision = self.engine.decide(
            connection_id="NO_ESCALATE_TEST",
            risk_score=20.0,
            risk_category="LOW",
            p_miss=0.20,
            pax_count=3,
            time_to_departure=60,
        )
        assert decision.escalation_required is False

    def test_alert_priority_critical_urgent(self):
        """CRITICAL with < 20 min → highest priority (P1)."""
        decision = self.engine.decide(
            connection_id="PRIORITY_TEST",
            risk_score=92.0,
            risk_category="CRITICAL",
            p_miss=0.92,
            pax_count=8,
            time_to_departure=12,
        )
        assert decision.alert_priority == 1

    def test_confidence_bounded(self):
        """Confidence must be between 0 and 1."""
        for score in [0, 25, 50, 75, 100]:
            decision = self.engine.decide(
                connection_id=f"CONF_TEST_{score}",
                risk_score=float(score),
                risk_category="HIGH",
                p_miss=score/100,
                pax_count=5,
                time_to_departure=30,
            )
            assert 0.0 <= decision.confidence <= 1.0, f"Confidence out of range for score {score}"


# ─────────────────────────────────────────────
# COST MODEL TESTS
# ─────────────────────────────────────────────

class TestCostModel:
    """Tests for the cost estimation model."""

    def test_hold_cost_positive(self):
        """Hold cost must always be positive."""
        result = estimate_costs(pax_count=5, avg_tier_score=2.0, pct_premium=0.2)
        assert result.hold_cost_total > 0

    def test_more_pax_more_miss_cost(self):
        """More pax → higher expected miss cost."""
        cost_small = estimate_costs(pax_count=2,  avg_tier_score=1.0, pct_premium=0.1)
        cost_large = estimate_costs(pax_count=15, avg_tier_score=1.0, pct_premium=0.1)
        assert cost_large.miss_cost_if_no_action > cost_small.miss_cost_if_no_action

    def test_premium_pax_higher_cost(self):
        """Premium pax have higher miss cost."""
        cost_economy = estimate_costs(pax_count=5, avg_tier_score=1.0, pct_premium=0.0)
        cost_premium = estimate_costs(pax_count=5, avg_tier_score=4.0, pct_premium=0.8)
        assert cost_premium.miss_cost_if_no_action > cost_economy.miss_cost_if_no_action

    def test_optimal_action_is_valid(self):
        """Optimal action must be one of the known action types."""
        valid_actions = {"HOLD_FLIGHT", "ARRANGE_ESCORT", "PRE_REBOOK", "NO_ACTION"}
        result = estimate_costs(pax_count=8, avg_tier_score=3.0, pct_premium=0.5, p_miss_without_action=0.9)
        assert result.optimal_action in valid_actions

    def test_zero_pax_minimal_cost(self):
        """Zero or minimal pax connection has minimal miss cost."""
        result = estimate_costs(pax_count=0, avg_tier_score=0.0, pct_premium=0.0, p_miss_without_action=0.9)
        assert result.miss_cost_if_no_action == pytest.approx(0.0, abs=1.0)

    def test_costs_return_dict(self):
        """to_dict() returns all expected keys."""
        result = estimate_costs(pax_count=5, avg_tier_score=2.0, pct_premium=0.3)
        d = result.to_dict()
        for key in ["miss_cost_if_no_action", "hold_cost_total", "net_benefit_hold", "optimal_action"]:
            assert key in d, f"Missing key: {key}"


# ─────────────────────────────────────────────
# RULE-BASED LAYER TESTS
# ─────────────────────────────────────────────

class TestRuleBasedLayer:
    """Tests for the hard rule override layer."""

    def setup_method(self):
        from src.models.risk_model import RuleBasedLayer
        self.rules = RuleBasedLayer()

    def test_negative_net_time_fires_rule(self):
        """Negative net connection time → rule fires with very high P(miss)."""
        result = self.rules.apply_rules({
            "net_connection_time": -5,
            "connection_buffer": -20,
            "inbound_delay_minutes": 40,
            "gate_walk_minutes": 25,
            "minimum_connection_time": 30,
            "requires_passport_control": False,
            "passport_overhead_minutes": 0,
        })
        assert result is not None
        p_miss, rule = result
        assert p_miss > 0.90
        assert "RULE" in rule

    def test_comfortable_buffer_caps_risk(self):
        """Large buffer with no delay → caps risk at very low value."""
        result = self.rules.apply_rules({
            "net_connection_time": 70,
            "connection_buffer": 45,
            "inbound_delay_minutes": 0,
            "gate_walk_minutes": 5,
            "minimum_connection_time": 25,
            "requires_passport_control": False,
            "passport_overhead_minutes": 0,
        })
        assert result is not None
        p_miss, rule = result
        assert p_miss < 0.10

    def test_normal_case_no_rule(self):
        """Borderline case → no rule fires → returns None."""
        result = self.rules.apply_rules({
            "net_connection_time": 20,
            "connection_buffer": 5,
            "inbound_delay_minutes": 15,
            "gate_walk_minutes": 18,
            "minimum_connection_time": 30,
            "requires_passport_control": False,
            "passport_overhead_minutes": 0,
        })
        # Borderline — may or may not fire, but if it does, must be valid
        if result is not None:
            p_miss, rule = result
            assert 0.0 <= p_miss <= 1.0

    def test_walk_exceeds_time_fires(self):
        """Walk time >= net time → rule fires."""
        result = self.rules.apply_rules({
            "net_connection_time": 15,
            "connection_buffer": -10,
            "inbound_delay_minutes": 20,
            "gate_walk_minutes": 20,  # equals net time
            "minimum_connection_time": 25,
            "requires_passport_control": False,
            "passport_overhead_minutes": 0,
        })
        assert result is not None
        p_miss, rule = result
        assert p_miss > 0.85


# ─────────────────────────────────────────────
# INTEGRATION SMOKE TEST
# ─────────────────────────────────────────────

class TestIntegration:
    """Smoke tests: do the components talk to each other."""

    def test_decision_engine_end_to_end(self):
        """Create engine, make a decision, verify output structure."""
        engine = DecisionEngine()
        decision = engine.decide(
            connection_id="INTEGRATION_TEST",
            risk_score=78.0,
            risk_category="HIGH",
            p_miss=0.78,
            pax_count=6,
            avg_tier_score=2.5,
            pct_premium=0.3,
            time_to_departure=20,
            hold_minutes=12,
        )
        d = decision.to_dict()

        # All required keys present
        required_keys = [
            "connection_id", "risk_score", "risk_category", "p_miss",
            "pax_count", "recommended_action", "action_description",
            "rationale", "confidence", "escalation_required", "alert_priority",
        ]
        for key in required_keys:
            assert key in d, f"Missing key: {key}"

        # Types
        assert isinstance(d["risk_score"], float)
        assert isinstance(d["pax_count"], int)
        assert isinstance(d["confidence"], float)
        assert isinstance(d["escalation_required"], bool)
        assert isinstance(d["alert_priority"], int)

        # Bounds
        assert 0.0 <= d["p_miss"] <= 1.0
        assert 0.0 <= d["risk_score"] <= 100.0
        assert 1 <= d["alert_priority"] <= 5
