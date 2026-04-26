"""
ConnectGuard — Decision Engine
================================
Translates risk scores into prioritized, cost-informed action recommendations.

This is the core product differentiator: not just predicting risk,
but telling ops teams WHAT TO DO about it, with business rationale.

Decision Framework:
  1. Risk threshold triggers candidate actions
  2. Cost-benefit model selects optimal action
  3. Downstream delay impact prevents over-holding
  4. Passenger tier weights final priority

Author: ConnectGuard Team
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
import random


# ─────────────────────────────────────────────
# ACTION TYPES
# ─────────────────────────────────────────────

class ActionType(str, Enum):
    HOLD_FLIGHT     = "HOLD_FLIGHT"
    ARRANGE_ESCORT  = "ARRANGE_ESCORT"
    PRE_REBOOK      = "PRE_REBOOK"
    MONITOR         = "MONITOR"
    NO_ACTION       = "NO_ACTION"


ACTION_DESCRIPTIONS = {
    ActionType.HOLD_FLIGHT:    "Hold outbound flight for connecting passengers",
    ActionType.ARRANGE_ESCORT: "Arrange priority escort / cart from inbound gate",
    ActionType.PRE_REBOOK:     "Proactively rebook passengers on next available flight",
    ActionType.MONITOR:        "Monitor connection — reassess in 10 minutes",
    ActionType.NO_ACTION:      "Connection is on track — no action required",
}

ACTION_PRIORITY = {
    ActionType.CRITICAL:     ActionType.HOLD_FLIGHT,
    ActionType.HIGH:         ActionType.ARRANGE_ESCORT,
    ActionType.MEDIUM:       ActionType.MONITOR,
    ActionType.LOW:          ActionType.NO_ACTION,
}

# Cost parameters (€)
REBOOK_COST_BASE      = 490.0    # economy passenger
REBOOK_COST_PREMIUM   = 1050.0   # business/first
EU261_PROBABILITY     = 0.55
EU261_AMOUNT_EUR      = 350.0
ESCORT_COST_PER_PAX   = 15.0
HOTEL_VOUCHER         = 150.0
MEAL_VOUCHER          = 22.0
HOLD_COST_PER_MINUTE  = 65.0     # fuel, crew, slot, propagation
DOWNSTREAM_COST_MULT  = 1.8      # multiplier for cascading effects


# ─────────────────────────────────────────────
# COST MODEL
# ─────────────────────────────────────────────

@dataclass
class CostEstimate:
    """Financial cost estimates for a decision."""

    # Cost of doing nothing (miss happens)
    miss_cost_if_no_action: float = 0.0

    # Cost of holding
    hold_cost_direct: float = 0.0
    hold_downstream_impact: float = 0.0
    hold_cost_total: float = 0.0

    # Cost of escort
    escort_cost: float = 0.0

    # Cost of pre-rebook
    rebook_cost_proactive: float = 0.0

    # Net benefit of each action
    net_benefit_hold:   float = 0.0
    net_benefit_escort: float = 0.0
    net_benefit_rebook: float = 0.0

    # Recommended action based on cost-benefit
    optimal_action: str = "NO_ACTION"

    def to_dict(self) -> dict:
        return {
            "miss_cost_if_no_action":   round(self.miss_cost_if_no_action, 2),
            "hold_cost_total":          round(self.hold_cost_total, 2),
            "escort_cost":              round(self.escort_cost, 2),
            "rebook_cost_proactive":    round(self.rebook_cost_proactive, 2),
            "net_benefit_hold":         round(self.net_benefit_hold, 2),
            "net_benefit_escort":       round(self.net_benefit_escort, 2),
            "net_benefit_rebook":       round(self.net_benefit_rebook, 2),
            "optimal_action":           self.optimal_action,
        }


def estimate_costs(
    pax_count: int,
    avg_tier_score: float,
    pct_premium: float,
    hold_minutes: int = 15,
    downstream_flights: int = 2,
    p_miss_without_action: float = 0.8,
) -> CostEstimate:
    """
    Compute cost estimates for all possible actions.

    Parameters
    ----------
    pax_count             : Number of connecting passengers
    avg_tier_score        : Average loyalty tier (0–5)
    pct_premium           : Fraction in business/first class
    hold_minutes          : How long flight would need to be held
    downstream_flights    : Downstream flights affected if we hold
    p_miss_without_action : P(miss) if no action taken

    Returns
    -------
    CostEstimate with all computed values
    """
    # ── Cost of a miss ────────────────────────────────────────────────
    avg_rebook_cost = (
        pct_premium * REBOOK_COST_PREMIUM +
        (1 - pct_premium) * REBOOK_COST_BASE
    )
    # Tier uplift: Senator pax cost more to lose (loyalty value)
    tier_uplift = avg_tier_score * 80.0  # up to €400 extra for HON Circle
    avg_rebook_cost += tier_uplift

    per_pax_miss_cost = (
        avg_rebook_cost
        + HOTEL_VOUCHER
        + MEAL_VOUCHER
        + EU261_PROBABILITY * EU261_AMOUNT_EUR
    )
    miss_cost = pax_count * per_pax_miss_cost * p_miss_without_action

    # ── Hold cost ─────────────────────────────────────────────────────
    hold_direct    = hold_minutes * HOLD_COST_PER_MINUTE
    hold_downstream = downstream_flights * hold_minutes * HOLD_COST_PER_MINUTE * DOWNSTREAM_COST_MULT
    hold_total     = hold_direct + hold_downstream

    # ── Escort cost ───────────────────────────────────────────────────
    escort_cost = pax_count * ESCORT_COST_PER_PAX + 30.0  # 30€ ops coordination

    # ── Proactive rebook cost ─────────────────────────────────────────
    # Proactive rebook is cheaper: no hotel needed if rebooked same day
    proactive_rebook_cost = pax_count * (avg_rebook_cost * 0.6 + MEAL_VOUCHER)

    # ── Net benefits ──────────────────────────────────────────────────
    # Benefit = expected cost saved vs doing nothing
    net_hold   = miss_cost - hold_total
    net_escort = miss_cost * 0.45 - escort_cost   # escort reduces P(miss) by ~45%
    net_rebook = miss_cost * 0.85 - proactive_rebook_cost  # rebook manages 85% of the cost

    # ── Optimal action ────────────────────────────────────────────────
    options = {
        "HOLD_FLIGHT":    net_hold,
        "ARRANGE_ESCORT": net_escort,
        "PRE_REBOOK":     net_rebook,
        "NO_ACTION":      0,
    }
    optimal = max(options, key=options.get)

    return CostEstimate(
        miss_cost_if_no_action  = miss_cost,
        hold_cost_direct        = hold_direct,
        hold_downstream_impact  = hold_downstream,
        hold_cost_total         = hold_total,
        escort_cost             = escort_cost,
        rebook_cost_proactive   = proactive_rebook_cost,
        net_benefit_hold        = net_hold,
        net_benefit_escort      = net_escort,
        net_benefit_rebook      = net_rebook,
        optimal_action          = optimal,
    )


# ─────────────────────────────────────────────
# DECISION ENGINE
# ─────────────────────────────────────────────

@dataclass
class DecisionOutput:
    """Structured output from the decision engine."""
    connection_id:       str
    risk_score:          float
    risk_category:       str
    p_miss:              float
    pax_count:           int
    recommended_action:  str
    action_description:  str
    rationale:           str
    cost_estimate:       dict
    confidence:          float       # 0–1 confidence in recommendation
    escalation_required: bool
    alert_priority:      int         # 1 (highest) to 5 (lowest)
    time_to_departure:   int         # minutes

    def to_dict(self) -> dict:
        return {
            "connection_id":       self.connection_id,
            "risk_score":          self.risk_score,
            "risk_category":       self.risk_category,
            "p_miss":              self.p_miss,
            "pax_count":           self.pax_count,
            "recommended_action":  self.recommended_action,
            "action_description":  self.action_description,
            "rationale":           self.rationale,
            "confidence":          self.confidence,
            "escalation_required": self.escalation_required,
            "alert_priority":      self.alert_priority,
            "time_to_departure":   self.time_to_departure,
            **self.cost_estimate,
        }


class DecisionEngine:
    """
    Converts risk scores into prioritized, cost-informed decisions.
    The PM-layer of the system: makes predictions actionable.
    """

    # Decision thresholds
    CRITICAL_THRESHOLD = 85
    HIGH_THRESHOLD     = 65
    MEDIUM_THRESHOLD   = 40
    LOW_THRESHOLD      = 0

    # Minimum pax count for hold decision
    MIN_PAX_FOR_HOLD   = 4

    # Maximum time before departure to recommend hold (after this, too late)
    MAX_TIME_FOR_HOLD  = 25  # minutes
    MIN_TIME_FOR_HOLD  = 8   # minutes (below this, impossible)

    @staticmethod
    def recommend(
        risk_score:        float,
        pax_count:         int,
        time_to_departure: int,
        avg_tier_score:    float = 1.0,
    ) -> str:
        """Simple action recommendation (string output)."""
        if risk_score >= DecisionEngine.CRITICAL_THRESHOLD:
            if time_to_departure >= DecisionEngine.MIN_TIME_FOR_HOLD:
                if pax_count >= DecisionEngine.MIN_PAX_FOR_HOLD:
                    return ActionType.HOLD_FLIGHT
                else:
                    return ActionType.PRE_REBOOK
            else:
                return ActionType.PRE_REBOOK

        elif risk_score >= DecisionEngine.HIGH_THRESHOLD:
            if time_to_departure >= 15:
                return ActionType.ARRANGE_ESCORT
            else:
                return ActionType.PRE_REBOOK

        elif risk_score >= DecisionEngine.MEDIUM_THRESHOLD:
            return ActionType.MONITOR

        else:
            return ActionType.NO_ACTION

    def decide(
        self,
        connection_id:     str,
        risk_score:        float,
        risk_category:     str,
        p_miss:            float,
        pax_count:         int,
        avg_tier_score:    float = 1.0,
        pct_premium:       float = 0.2,
        time_to_departure: int   = 30,
        hold_minutes:      int   = 15,
        downstream_flights: int  = 2,
        rule_triggered:    Optional[str] = None,
    ) -> DecisionOutput:
        """
        Full decision with cost analysis and rationale.

        Returns a DecisionOutput with all context an ops controller needs.
        """
        # Compute cost estimates
        costs = estimate_costs(
            pax_count             = pax_count,
            avg_tier_score        = avg_tier_score,
            pct_premium           = pct_premium,
            hold_minutes          = hold_minutes,
            downstream_flights    = downstream_flights,
            p_miss_without_action = p_miss,
        )

        # Primary recommendation from rule
        action = self.recommend(risk_score, pax_count, time_to_departure, avg_tier_score)

        # Override with cost-optimal if strongly differs
        cost_optimal = costs.optimal_action
        if (
            action == ActionType.HOLD_FLIGHT
            and costs.net_benefit_hold < 0
            and costs.net_benefit_rebook > costs.net_benefit_hold
        ):
            action = ActionType.PRE_REBOOK

        # Build rationale string
        rationale = self._build_rationale(
            action, risk_score, p_miss, pax_count,
            costs, time_to_departure, rule_triggered
        )

        # Confidence calculation
        confidence = self._compute_confidence(risk_score, rule_triggered, pax_count, time_to_departure)

        # Alert priority (1=highest)
        priority = self._alert_priority(risk_score, avg_tier_score, time_to_departure)

        # Escalation required for CRITICAL with short time window
        escalation = (risk_score >= self.CRITICAL_THRESHOLD and time_to_departure < 20)

        return DecisionOutput(
            connection_id      = connection_id,
            risk_score         = round(risk_score, 2),
            risk_category      = risk_category,
            p_miss             = round(p_miss, 4),
            pax_count          = pax_count,
            recommended_action = action,
            action_description = ACTION_DESCRIPTIONS.get(action, ""),
            rationale          = rationale,
            cost_estimate      = costs.to_dict(),
            confidence         = round(confidence, 3),
            escalation_required = escalation,
            alert_priority     = priority,
            time_to_departure  = time_to_departure,
        )

    def _build_rationale(
        self,
        action: str,
        risk_score: float,
        p_miss: float,
        pax_count: int,
        costs: CostEstimate,
        time_to_dep: int,
        rule_triggered: Optional[str],
    ) -> str:
        """Human-readable rationale for the decision."""
        base = f"Risk score {risk_score:.0f}/100 ({p_miss:.0%} miss probability). {pax_count} connecting pax. {time_to_dep} min to departure. "

        if rule_triggered:
            base += f"Hard rule triggered: {rule_triggered}. "

        if action == ActionType.HOLD_FLIGHT:
            net = costs.net_benefit_hold
            base += f"Hold recommended: saves estimated €{costs.miss_cost_if_no_action:,.0f} vs €{costs.hold_cost_total:,.0f} hold cost (net benefit: €{net:,.0f})."
        elif action == ActionType.ARRANGE_ESCORT:
            base += f"Escort at €{costs.escort_cost:.0f} can reduce miss probability by ~45%. Insufficient pax or time for hold."
        elif action == ActionType.PRE_REBOOK:
            base += f"Miss is likely inevitable. Proactive rebook (€{costs.rebook_cost_proactive:,.0f}) prevents stranding. Saves EU261 liability."
        elif action == ActionType.MONITOR:
            base += f"Buffer still adequate. Reassess in 10 minutes if delay worsens."
        else:
            base += f"Connection on track. No intervention required."

        return base

    def _compute_confidence(
        self,
        risk_score: float,
        rule_triggered: Optional[str],
        pax_count: int,
        time_to_dep: int,
    ) -> float:
        """Confidence in the recommendation (0–1)."""
        base = 0.70

        # Rule-based triggers have higher confidence
        if rule_triggered:
            base += 0.20

        # Very high or very low scores are more confident
        if risk_score > 85 or risk_score < 20:
            base += 0.10
        elif 40 < risk_score < 70:
            base -= 0.10  # borderline cases are less certain

        # More pax = more data signal
        if pax_count > 8:
            base += 0.05

        # Tight time windows reduce confidence (less time to verify)
        if time_to_dep < 10:
            base -= 0.10

        return max(0.40, min(1.0, base))

    def _alert_priority(
        self,
        risk_score: float,
        avg_tier_score: float,
        time_to_dep: int,
    ) -> int:
        """1 = immediate action, 5 = informational."""
        if risk_score >= 85 and time_to_dep < 20:
            return 1
        elif risk_score >= 85:
            return 2
        elif risk_score >= 65 and avg_tier_score >= 3.5:
            return 2  # high risk with Senator/HON pax
        elif risk_score >= 65:
            return 3
        elif risk_score >= 40:
            return 4
        else:
            return 5


# ─────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────

if __name__ == "__main__":
    engine = DecisionEngine()

    scenarios = [
        {
            "name":              "Longhaul CRITICAL — Senator pax",
            "connection_id":     "LH721_LH400_20240315",
            "risk_score":        91.0,
            "risk_category":     "CRITICAL",
            "p_miss":            0.91,
            "pax_count":         8,
            "avg_tier_score":    3.8,
            "pct_premium":       0.5,
            "time_to_departure": 18,
            "hold_minutes":      18,
            "downstream_flights": 1,
        },
        {
            "name":              "Borderline HIGH — Economy pax",
            "connection_id":     "LH300_LH55_20240315",
            "risk_score":        72.0,
            "risk_category":     "HIGH",
            "p_miss":            0.72,
            "pax_count":         3,
            "avg_tier_score":    1.0,
            "pct_premium":       0.0,
            "time_to_departure": 28,
            "hold_minutes":      12,
            "downstream_flights": 2,
        },
        {
            "name":              "LOW RISK — comfortable buffer",
            "connection_id":     "LH500_LH600_20240315",
            "risk_score":        18.0,
            "risk_category":     "LOW",
            "p_miss":            0.18,
            "pax_count":         5,
            "avg_tier_score":    1.5,
            "pct_premium":       0.1,
            "time_to_departure": 60,
            "hold_minutes":      0,
            "downstream_flights": 0,
        },
    ]

    for s in scenarios:
        print(f"\n{'='*60}")
        print(f"  SCENARIO: {s['name']}")
        print(f"{'='*60}")
        decision = engine.decide(**{k: v for k, v in s.items() if k != "name"})
        d = decision.to_dict()
        print(f"  Action:      {d['recommended_action']}")
        print(f"  Confidence:  {d['confidence']:.0%}")
        print(f"  Priority:    P{d['alert_priority']}")
        print(f"  Escalation:  {d['escalation_required']}")
        print(f"  Miss cost:   €{d['miss_cost_if_no_action']:,.0f}")
        print(f"  Net benefit: €{d['net_benefit_hold']:,.0f} (hold)")
        print(f"  Rationale:   {d['rationale']}")
