"""
ConnectGuard — Synthetic Data Generator
========================================
Generates realistic synthetic data for the Frankfurt (FRA) hub connection scenario.
Simulates flight schedules, delays, connection pairs, passenger profiles, and outcomes.

Author: ConnectGuard Team
Usage:
    python data/generate_synthetic_data.py
    python data/generate_synthetic_data.py --days 30 --seed 99
"""

import argparse
import os
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────
HUB = "FRA"
SIMULATION_DAYS = 90
RANDOM_SEED = 42
DAILY_CONNECTIONS = 800

BASELINE_MISS_RATE = 0.021     # 2.1% normal ops
IROP_DAY_PROBABILITY = 0.15    # 15% of days are IROP disrupted
IROP_MISS_RATE = 0.085         # 8.5% miss rate on IROP days

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "synthetic")

# Frankfurt terminal and gate structure
TERMINALS = ["T1", "T2"]
TERMINAL_GATES = {
    "T1": [f"A{i}" for i in range(1, 26)] + [f"B{i}" for i in range(1, 20)] + [f"C{i}" for i in range(1, 30)],
    "T2": [f"D{i}" for i in range(1, 20)] + [f"E{i}" for i in range(1, 30)] + [f"Z{i}" for i in range(50, 80)],
}

# MCT by terminal crossing type (minutes)
MCT_MATRIX = {
    ("T1", "T1", False): 30,   # domestic-to-domestic, same terminal
    ("T1", "T1", True): 45,    # international, same terminal
    ("T1", "T2", False): 40,   # terminal crossing
    ("T1", "T2", True): 55,
    ("T2", "T1", False): 40,
    ("T2", "T1", True): 55,
    ("T2", "T2", False): 30,
    ("T2", "T2", True): 45,
}

# Inbound origins (short-haul feeders)
INBOUND_ORIGINS = [
    "MUC", "HAM", "BER", "DUS", "CGN", "STR", "NUE",  # German domestic
    "LHR", "CDG", "AMS", "ZRH", "VIE", "BRU", "MAD",  # European
    "IST", "ATH", "WAW", "PRG", "BUD",                  # Eastern European
]

# Outbound destinations (longhaul)
OUTBOUND_DESTINATIONS = [
    "JFK", "EWR", "ORD", "LAX", "MIA", "BOS",   # North America
    "NRT", "HKG", "PEK", "SIN", "BOM", "DEL",   # Asia
    "DXB", "DOH", "RUH", "CAI",                   # Middle East
    "GRU", "BOG", "LIM",                           # South America
    "JNB", "NBO", "LOS",                           # Africa
]

LOYALTY_TIERS = ["None", "Member", "Silver", "Gold", "Senator", "HON Circle"]
TIER_SCORES   = [0,       1,        2,        3,      4,          5]
SEAT_CLASSES  = ["Economy", "Economy", "Economy", "Business", "First"]  # weighted

AIRCRAFT_TYPES = ["A320", "A321", "B737", "A319", "E190", "A380", "B777", "B747", "A350"]

DELAY_BUCKETS = [
    (0.55, 0, 0),         # no delay
    (0.25, 5, 20),        # minor
    (0.13, 21, 60),       # moderate
    (0.07, 61, 180),      # severe
]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def generate_flight_id(carrier: str, number: int) -> str:
    return f"{carrier}{number:04d}"


def sample_delay(is_irop: bool) -> int:
    """Sample delay in minutes based on operational context."""
    if is_irop:
        # On IROP days, shift distribution toward moderate/severe
        buckets = [(0.30, 0, 0), (0.30, 5, 30), (0.25, 31, 90), (0.15, 91, 240)]
    else:
        buckets = DELAY_BUCKETS

    r = random.random()
    cumulative = 0.0
    for prob, lo, hi in buckets:
        cumulative += prob
        if r < cumulative:
            return 0 if lo == 0 and hi == 0 else random.randint(lo, hi)
    return 0


def gate_walk_time(gate_in: str, gate_out: str) -> int:
    """
    Estimate gate walking time.
    Uses prefix letter to approximate hub geography.
    A/B/C = T1, D/E/Z = T2.
    """
    same_zone = gate_in[0] == gate_out[0]
    terminal_in  = "T1" if gate_in[0]  in ("A", "B", "C") else "T2"
    terminal_out = "T2" if gate_out[0] in ("D", "E", "Z") else "T1"
    same_terminal = terminal_in == terminal_out

    if same_zone:
        return random.randint(3, 10)
    elif same_terminal:
        return random.randint(8, 20)
    else:
        return random.randint(18, 35)  # cross-terminal requires shuttle


def compute_risk_score(
    delay_minutes: int,
    scheduled_connection_min: int,
    gate_walk_minutes: int,
    passport_overhead: int,
    mct: int,
    pax_tier_score: float,
) -> float:
    """
    Rule + probabilistic hybrid risk score.
    Returns a value in [0, 100].
    """
    net_time = scheduled_connection_min - delay_minutes - gate_walk_minutes - passport_overhead
    buffer   = net_time - mct

    # Base score from buffer gap
    if buffer >= 30:
        base = random.uniform(0, 25)
    elif buffer >= 15:
        base = random.uniform(15, 45)
    elif buffer >= 5:
        base = random.uniform(35, 65)
    elif buffer >= 0:
        base = random.uniform(55, 80)
    else:
        base = random.uniform(75, 100)

    # Adjust downward for premium pax (more escorted, more likely to make it)
    tier_adjustment = pax_tier_score * 1.5  # up to 7.5 pts reduction
    score = base - tier_adjustment

    # Add a little noise
    score += random.gauss(0, 3)
    return max(0.0, min(100.0, score))


def risk_category(score: float) -> str:
    if score < 30:
        return "LOW"
    elif score < 65:
        return "MEDIUM"
    elif score < 85:
        return "HIGH"
    else:
        return "CRITICAL"


def recommend_action(score: float, pax_count: int, time_to_dep: int) -> str:
    """Decision engine recommendation."""
    if score >= 85 and time_to_dep > 20 and pax_count >= 5:
        return "HOLD_FLIGHT"
    elif score >= 85 and time_to_dep <= 20:
        return "PRE_REBOOK"
    elif score >= 65 and time_to_dep > 15:
        return "ARRANGE_ESCORT"
    elif score >= 65 and time_to_dep <= 15:
        return "PRE_REBOOK"
    elif score >= 40:
        return "MONITOR"
    else:
        return "NO_ACTION"


def compute_costs(pax_count: int, avg_tier: float, action: str) -> dict:
    """Estimate cost values for a connection."""
    avg_rebook_cost = 490 + (avg_tier * 120)  # premium pax cost more
    eu261_probability = 0.55  # ~55% of missed connections qualify for EU261
    eu261_amount = 350

    save_value = pax_count * (avg_rebook_cost + eu261_probability * eu261_amount)

    hold_cost_map = {
        "HOLD_FLIGHT": random.uniform(300, 1500),  # fuel + slot + delay propagation
        "ARRANGE_ESCORT": pax_count * 15,
        "PRE_REBOOK": pax_count * 50,
        "MONITOR": 0,
        "NO_ACTION": 0,
    }
    hold_cost = hold_cost_map.get(action, 0)

    return {
        "estimated_save_value": round(save_value, 2),
        "estimated_hold_cost": round(hold_cost, 2),
        "net_benefit": round(save_value - hold_cost, 2),
    }


def simulate_outcome(risk_score: float, action: str, is_irop: bool) -> dict:
    """Determine if connection was made or missed, and actual cost."""
    p_miss_base = risk_score / 100.0

    # Actions reduce P(miss)
    action_reduction = {
        "HOLD_FLIGHT": 0.80,
        "ARRANGE_ESCORT": 0.40,
        "PRE_REBOOK": 0.0,    # inevitable miss, but handled
        "MONITOR": 0.05,
        "NO_ACTION": 0.0,
    }
    p_miss_effective = p_miss_base * (1 - action_reduction.get(action, 0))

    missed = random.random() < p_miss_effective

    if action == "PRE_REBOOK":
        result = "MISSED_MANAGED"
        cost = random.uniform(50, 150)  # handled proactively, low cost
    elif missed:
        result = "MISSED"
        cost = random.uniform(350, 850)
    else:
        result = "CONNECTION_MADE"
        cost = random.uniform(0, 50)  # escort/hold cost

    return {"result": result, "actual_cost": round(cost, 2)}


# ─────────────────────────────────────────────
# GENERATORS
# ─────────────────────────────────────────────

def generate_flights(start_date: datetime, n_days: int) -> pd.DataFrame:
    """Generate inbound feeder flights arriving at FRA."""
    rows = []
    flight_num = 1000

    for day_offset in range(n_days):
        date = start_date + timedelta(days=day_offset)
        is_irop = random.random() < IROP_DAY_PROBABILITY

        # ~400 inbound connections per day
        for _ in range(DAILY_CONNECTIONS):
            origin = random.choice(INBOUND_ORIGINS)
            terminal = random.choice(TERMINALS)
            gate = random.choice(TERMINAL_GATES[terminal])

            # Spread arrivals throughout the day (05:00–22:00)
            arrival_hour   = random.randint(5, 21)
            arrival_minute = random.randint(0, 59)
            sched_arrival  = date.replace(hour=arrival_hour, minute=arrival_minute, second=0, microsecond=0)

            delay = sample_delay(is_irop)
            est_arrival    = sched_arrival + timedelta(minutes=delay)

            carrier = random.choice(["LH", "LX", "OS", "4U"])
            fid = generate_flight_id(carrier, flight_num)
            flight_num += 1

            rows.append({
                "flight_id":           fid,
                "flight_number":       fid,
                "origin":              origin,
                "destination":         HUB,
                "scheduled_arrival":   sched_arrival,
                "estimated_arrival":   est_arrival,
                "actual_arrival":      est_arrival + timedelta(minutes=random.randint(-2, 5)),
                "delay_minutes":       delay,
                "gate_arrival":        gate,
                "terminal_arrival":    terminal,
                "aircraft_type":       random.choice(AIRCRAFT_TYPES),
                "is_international":    origin not in ["MUC", "HAM", "BER", "DUS", "CGN", "STR", "NUE"],
                "is_irop_day":         is_irop,
                "date":                date.date(),
            })

    return pd.DataFrame(rows)


def generate_connections(flights_df: pd.DataFrame) -> pd.DataFrame:
    """Generate outbound connections for each inbound flight."""
    rows = []
    conn_num = 1

    for _, inbound in flights_df.iterrows():
        dest = random.choice(OUTBOUND_DESTINATIONS)
        out_terminal = random.choice(TERMINALS)
        out_gate = random.choice(TERMINAL_GATES[out_terminal])

        connection_window = random.randint(45, 150)  # scheduled time between flights
        outbound_dep = inbound["scheduled_arrival"] + timedelta(minutes=connection_window)

        in_terminal = inbound["terminal_arrival"]
        in_gate     = inbound["gate_arrival"]
        requires_passport = inbound["is_international"] or dest not in ["MUC", "HAM", "BER"]

        mct = MCT_MATRIX.get((in_terminal, out_terminal, requires_passport), 45)
        walk_time = gate_walk_time(in_gate, out_gate)
        passport_oh = random.randint(10, 20) if requires_passport else 0

        out_carrier = random.choice(["LH", "LX", "OS"])
        out_fid = generate_flight_id(out_carrier, 5000 + conn_num)

        rows.append({
            "connection_id":              f"{inbound['flight_id']}_{out_fid}_{inbound['date']}",
            "inbound_flight_id":          inbound["flight_id"],
            "outbound_flight_id":         out_fid,
            "outbound_destination":       dest,
            "connecting_airport":         HUB,
            "inbound_arrival_gate":       in_gate,
            "inbound_terminal":           in_terminal,
            "outbound_departure_gate":    out_gate,
            "outbound_terminal":          out_terminal,
            "outbound_scheduled_dep":     outbound_dep,
            "scheduled_connection_time":  connection_window,
            "minimum_connection_time":    mct,
            "gate_walk_minutes":          walk_time,
            "requires_passport_control":  requires_passport,
            "passport_overhead_minutes":  passport_oh,
            "inbound_delay_minutes":      inbound["delay_minutes"],
            "is_irop_day":                inbound["is_irop_day"],
            "date":                       inbound["date"],
        })
        conn_num += 1

    return pd.DataFrame(rows)


def generate_passengers(connections_df: pd.DataFrame) -> pd.DataFrame:
    """Generate passenger records for each connection."""
    rows = []
    pax_num = 1

    for _, conn in connections_df.iterrows():
        # 1–18 connecting passengers per pair
        n_pax = random.randint(1, 18)

        for _ in range(n_pax):
            tier_idx  = random.choices(range(6), weights=[40, 25, 15, 10, 7, 3])[0]
            seat_cls  = random.choices(SEAT_CLASSES)[0]

            rows.append({
                "passenger_id":      f"PAX_{pax_num:06d}",
                "connection_id":     conn["connection_id"],
                "loyalty_tier":      LOYALTY_TIERS[tier_idx],
                "tier_score":        TIER_SCORES[tier_idx],
                "seat_class":        seat_cls,
                "mobility_assistance": random.random() < 0.04,  # 4% need assistance
                "nationality":       random.choice(["DE", "US", "GB", "FR", "CN", "IN", "TR", "BR"]),
                "requires_visa":     random.random() < 0.12,
            })
            pax_num += 1

    return pd.DataFrame(rows)


def generate_risk_scores(connections_df: pd.DataFrame, passengers_df: pd.DataFrame) -> pd.DataFrame:
    """Generate risk scores for each connection."""
    rows = []

    # Compute average tier score per connection
    avg_tier = passengers_df.groupby("connection_id")["tier_score"].mean().to_dict()
    pax_count = passengers_df.groupby("connection_id").size().to_dict()

    for _, conn in connections_df.iterrows():
        cid = conn["connection_id"]
        tier = avg_tier.get(cid, 1.0)
        n_pax = pax_count.get(cid, 3)

        score = compute_risk_score(
            delay_minutes            = conn["inbound_delay_minutes"],
            scheduled_connection_min = conn["scheduled_connection_time"],
            gate_walk_minutes        = conn["gate_walk_minutes"],
            passport_overhead        = conn["passport_overhead_minutes"],
            mct                      = conn["minimum_connection_time"],
            pax_tier_score           = tier,
        )

        category = risk_category(score)
        time_to_dep = conn["scheduled_connection_time"] - conn["inbound_delay_minutes"]
        action = recommend_action(score, n_pax, time_to_dep)

        costs = compute_costs(n_pax, tier, action)

        rows.append({
            "score_id":              f"SCORE_{len(rows)+1:06d}",
            "connection_id":         cid,
            "scored_at":             conn["outbound_scheduled_dep"] - timedelta(minutes=random.randint(30, 90)),
            "risk_score":            round(score, 2),
            "risk_category":         category,
            "p_miss":                round(score / 100.0, 4),
            "recommended_action":    action,
            "pax_count":             n_pax,
            "avg_tier_score":        round(tier, 2),
            "time_to_departure_min": max(0, int(time_to_dep)),
            **costs,
        })

    return pd.DataFrame(rows)


def generate_outcomes(risk_scores_df: pd.DataFrame, connections_df: pd.DataFrame) -> pd.DataFrame:
    """Simulate what actually happened for each connection."""
    is_irop = connections_df.set_index("connection_id")["is_irop_day"].to_dict()
    rows = []

    controllers = ["OPS_K_BRAUN", "OPS_M_SCHMIDT", "OPS_A_WEBER", "OPS_T_VOGEL"]

    for _, score in risk_scores_df.iterrows():
        irop = is_irop.get(score["connection_id"], False)
        outcome = simulate_outcome(score["risk_score"], score["recommended_action"], irop)

        ack_delay = random.randint(2, 25) if score["risk_score"] > 40 else None
        ack_time  = (score["scored_at"] + timedelta(minutes=ack_delay)) if ack_delay else None

        rows.append({
            "outcome_id":             f"OUT_{len(rows)+1:06d}",
            "connection_id":          score["connection_id"],
            "risk_score_at_decision": score["risk_score"],
            "action_taken":           score["recommended_action"],
            "result":                 outcome["result"],
            "actual_cost":            outcome["actual_cost"],
            "alert_acknowledged_at":  ack_time,
            "controller_id":          random.choice(controllers) if ack_time else None,
        })

    return pd.DataFrame(rows)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main(days: int = SIMULATION_DAYS, seed: int = RANDOM_SEED):
    random.seed(seed)
    np.random.seed(seed)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    start_date = datetime(2024, 1, 1)

    print(f"[ConnectGuard] Generating {days} days of synthetic data (seed={seed})...")
    print(f"[1/5] Generating flights...")
    flights_df = generate_flights(start_date, days)
    flights_df.to_csv(os.path.join(OUTPUT_DIR, "flights.csv"), index=False)
    print(f"       → {len(flights_df):,} inbound flight records")

    print(f"[2/5] Generating connection pairs...")
    connections_df = generate_connections(flights_df)
    connections_df.to_csv(os.path.join(OUTPUT_DIR, "connections.csv"), index=False)
    print(f"       → {len(connections_df):,} connection pairs")

    print(f"[3/5] Generating passengers...")
    passengers_df = generate_passengers(connections_df)
    passengers_df.to_csv(os.path.join(OUTPUT_DIR, "passengers.csv"), index=False)
    print(f"       → {len(passengers_df):,} passenger records")

    print(f"[4/5] Generating risk scores...")
    risk_scores_df = generate_risk_scores(connections_df, passengers_df)
    risk_scores_df.to_csv(os.path.join(OUTPUT_DIR, "risk_scores.csv"), index=False)
    print(f"       → {len(risk_scores_df):,} risk score records")

    print(f"[5/5] Generating outcomes...")
    outcomes_df = generate_outcomes(risk_scores_df, connections_df)
    outcomes_df.to_csv(os.path.join(OUTPUT_DIR, "outcomes.csv"), index=False)
    print(f"       → {len(outcomes_df):,} outcome records")

    # Summary statistics
    missed = outcomes_df[outcomes_df["result"] == "MISSED"]
    made   = outcomes_df[outcomes_df["result"] == "CONNECTION_MADE"]
    managed = outcomes_df[outcomes_df["result"] == "MISSED_MANAGED"]

    print("\n" + "="*50)
    print("  SIMULATION SUMMARY")
    print("="*50)
    print(f"  Days simulated:      {days}")
    print(f"  Total connections:   {len(connections_df):,}")
    print(f"  Made:                {len(made):,} ({len(made)/len(outcomes_df)*100:.1f}%)")
    print(f"  Missed:              {len(missed):,} ({len(missed)/len(outcomes_df)*100:.1f}%)")
    print(f"  Missed (managed):    {len(managed):,} ({len(managed)/len(outcomes_df)*100:.1f}%)")
    print(f"  Total direct cost:   €{outcomes_df['actual_cost'].sum():,.0f}")
    print(f"\n  Output directory: {OUTPUT_DIR}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ConnectGuard synthetic data")
    parser.add_argument("--days",  type=int, default=SIMULATION_DAYS, help="Simulation days")
    parser.add_argument("--seed",  type=int, default=RANDOM_SEED,     help="Random seed")
    args = parser.parse_args()
    main(days=args.days, seed=args.seed)
