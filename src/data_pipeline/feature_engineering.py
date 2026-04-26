"""
ConnectGuard — Feature Engineering Pipeline
=============================================
Transforms raw connection and flight data into model-ready features.
Handles both batch processing (historical) and near-real-time scoring.

Author: ConnectGuard Team
"""

import pandas as pd
import numpy as np
from typing import Optional


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

TIER_SCORE_MAP = {
    "None": 0, "Member": 1, "Silver": 2,
    "Gold": 3, "Senator": 4, "HON Circle": 5,
}

SEAT_CLASS_WEIGHT = {
    "Economy": 1.0,
    "Business": 2.5,
    "First": 4.0,
}

# Empirical miss rate by time-of-day bucket (from historical analysis)
PEAK_HOUR_RISK_MULTIPLIER = {
    "morning_bank": 1.3,   # 06:00–09:00 — peak connection bank, high congestion
    "midday":       0.9,   # 09:00–13:00 — moderate
    "afternoon":    1.0,   # 13:00–17:00 — baseline
    "evening_bank": 1.2,   # 17:00–20:00 — second peak
    "night":        0.7,   # 20:00–06:00 — quieter ops
}

ROUTE_HISTORICAL_MISS_RATES = {
    # Feeder-to-longhaul pairs: estimated historical miss rates
    ("FRA", "JFK"): 0.025,
    ("FRA", "NRT"): 0.018,
    ("FRA", "DXB"): 0.031,
    ("FRA", "GRU"): 0.029,
    ("FRA", "JNB"): 0.022,
}


# ─────────────────────────────────────────────
# FEATURE ENGINEERING
# ─────────────────────────────────────────────

class FeatureEngineer:
    """
    Transforms raw DataFrames into feature matrices suitable for
    risk model training and inference.
    """

    def __init__(self, gate_distance_matrix: Optional[pd.DataFrame] = None):
        """
        Parameters
        ----------
        gate_distance_matrix : Optional DataFrame with gate-to-gate walk times.
                               If None, estimated times are used.
        """
        self.gate_distance_matrix = gate_distance_matrix

    # ── Core feature computation ──────────────────────────────────────

    def compute_net_connection_time(self, row: pd.Series) -> float:
        """
        Net connection time = scheduled_connection_time - delay - walk - passport.
        Negative values indicate buffer is already exhausted.
        """
        return (
            row["scheduled_connection_time"]
            - row["inbound_delay_minutes"]
            - row["gate_walk_minutes"]
            - row["passport_overhead_minutes"]
        )

    def compute_connection_buffer(self, row: pd.Series) -> float:
        """Buffer above MCT. Negative = already below MCT."""
        net = self.compute_net_connection_time(row)
        return net - row["minimum_connection_time"]

    def delay_ratio(self, row: pd.Series) -> float:
        """Inbound delay as fraction of scheduled connection time."""
        if row["scheduled_connection_time"] == 0:
            return 1.0
        return min(1.0, row["inbound_delay_minutes"] / row["scheduled_connection_time"])

    def time_of_day_bucket(self, hour: int) -> str:
        """Classify hour into operational period."""
        if 6 <= hour < 9:
            return "morning_bank"
        elif 9 <= hour < 13:
            return "midday"
        elif 13 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 20:
            return "evening_bank"
        else:
            return "night"

    def get_peak_multiplier(self, hour: int) -> float:
        bucket = self.time_of_day_bucket(hour)
        return PEAK_HOUR_RISK_MULTIPLIER[bucket]

    def compute_urgency_score(self, row: pd.Series) -> float:
        """
        Time-pressure component: how rapidly the window is closing.
        0 = plenty of time, 1 = imminent.
        """
        buffer = self.compute_connection_buffer(row)
        if buffer >= 30:
            return 0.0
        elif buffer >= 15:
            return 0.25
        elif buffer >= 5:
            return 0.55
        elif buffer >= 0:
            return 0.80
        else:
            return 1.0

    def is_cross_terminal(self, row: pd.Series) -> bool:
        """Check if connection requires terminal change."""
        t_in  = row.get("inbound_terminal", "T1")
        t_out = row.get("outbound_terminal", "T1")
        return t_in != t_out

    # ── Passenger aggregation ─────────────────────────────────────────

    def aggregate_passenger_features(self, passengers_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate passenger-level data to connection level.
        Returns DataFrame indexed by connection_id.
        """
        agg = passengers_df.groupby("connection_id").agg(
            pax_count           = ("passenger_id", "count"),
            avg_tier_score      = ("tier_score", "mean"),
            max_tier_score      = ("tier_score", "max"),
            pct_premium         = ("seat_class", lambda x: (x.isin(["Business", "First"])).mean()),
            has_mobility_pax    = ("mobility_assistance", "any"),
            has_senator         = ("loyalty_tier", lambda x: x.isin(["Senator", "HON Circle"]).any()),
            pct_visa_required   = ("requires_visa", "mean"),
        ).reset_index()

        # Compute weighted tier score (emphasizes premium mix)
        agg["weighted_tier_score"] = (
            agg["avg_tier_score"] * 0.6 + agg["max_tier_score"] * 0.4
        )

        return agg

    # ── Master feature builder ────────────────────────────────────────

    def build_features(
        self,
        connections_df: pd.DataFrame,
        passengers_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Build full feature matrix for model training or inference.

        Parameters
        ----------
        connections_df : Connection pairs DataFrame
        passengers_df  : Passenger DataFrame

        Returns
        -------
        Feature DataFrame ready for model input.
        """
        df = connections_df.copy()

        # Merge passenger aggregates
        pax_agg = self.aggregate_passenger_features(passengers_df)
        df = df.merge(pax_agg, on="connection_id", how="left")

        # Fill missing pax data with defaults
        df["pax_count"]        = df["pax_count"].fillna(3)
        df["avg_tier_score"]   = df["avg_tier_score"].fillna(1.0)
        df["weighted_tier_score"] = df["weighted_tier_score"].fillna(1.0)
        df["pct_premium"]      = df["pct_premium"].fillna(0.0)
        df["has_senator"]      = df["has_senator"].fillna(False)
        df["has_mobility_pax"] = df["has_mobility_pax"].fillna(False)
        df["pct_visa_required"]= df["pct_visa_required"].fillna(0.1)

        # ── Temporal features ────────────────────────────────────────
        if "outbound_scheduled_dep" in df.columns:
            df["outbound_scheduled_dep"] = pd.to_datetime(df["outbound_scheduled_dep"])
            df["departure_hour"] = df["outbound_scheduled_dep"].dt.hour
            df["day_of_week"]    = df["outbound_scheduled_dep"].dt.dayofweek
            df["is_weekend"]     = df["day_of_week"].isin([5, 6]).astype(int)
        else:
            df["departure_hour"] = 12
            df["day_of_week"]    = 0
            df["is_weekend"]     = 0

        df["peak_multiplier"] = df["departure_hour"].apply(self.get_peak_multiplier)

        # ── Connection time features ──────────────────────────────────
        df["net_connection_time"] = df.apply(self.compute_net_connection_time, axis=1)
        df["connection_buffer"]   = df.apply(self.compute_connection_buffer, axis=1)
        df["delay_ratio"]         = df.apply(self.delay_ratio, axis=1)
        df["urgency_score"]       = df.apply(self.compute_urgency_score, axis=1)
        df["is_cross_terminal"]   = df.apply(self.is_cross_terminal, axis=1).astype(int)

        # ── Derived risk factors ──────────────────────────────────────
        df["delay_exceeds_buffer"] = (df["inbound_delay_minutes"] > df["connection_buffer"]).astype(int)
        df["below_mct"]            = (df["net_connection_time"] < df["minimum_connection_time"]).astype(int)
        df["walk_fraction"]        = df["gate_walk_minutes"] / (df["scheduled_connection_time"] + 1)

        # Passenger load factor (high pax count with tight connection = harder to manage)
        df["high_pax_tight_connection"] = (
            (df["pax_count"] > 8) & (df["connection_buffer"] < 10)
        ).astype(int)

        # ── Historical base rate ──────────────────────────────────────
        df["historical_miss_rate"] = 0.021  # default
        # Could be enriched with actual route-level data

        # ── Final feature columns for model ──────────────────────────
        return df

    def get_feature_columns(self) -> list:
        """Return ordered list of model input features."""
        return [
            # Time and delay
            "inbound_delay_minutes",
            "scheduled_connection_time",
            "net_connection_time",
            "connection_buffer",
            "delay_ratio",
            "urgency_score",

            # Gate / routing
            "gate_walk_minutes",
            "walk_fraction",
            "minimum_connection_time",
            "is_cross_terminal",
            "requires_passport_control",
            "passport_overhead_minutes",

            # Passenger composition
            "pax_count",
            "avg_tier_score",
            "weighted_tier_score",
            "pct_premium",
            "has_senator",
            "has_mobility_pax",
            "pct_visa_required",

            # Derived risk flags
            "delay_exceeds_buffer",
            "below_mct",
            "high_pax_tight_connection",

            # Temporal
            "departure_hour",
            "day_of_week",
            "is_weekend",
            "peak_multiplier",

            # Historical
            "historical_miss_rate",
        ]


# ─────────────────────────────────────────────
# CONVENIENCE FUNCTION
# ─────────────────────────────────────────────

def build_feature_matrix(
    connections_path: str,
    passengers_path: str,
) -> pd.DataFrame:
    """
    Utility function: load CSVs and return feature-engineered DataFrame.
    """
    connections_df = pd.read_csv(connections_path)
    passengers_df  = pd.read_csv(passengers_path)

    fe = FeatureEngineer()
    return fe.build_features(connections_df, passengers_df)


if __name__ == "__main__":
    import os

    SYNTHETIC_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
    conn_path = os.path.join(SYNTHETIC_DIR, "connections.csv")
    pax_path  = os.path.join(SYNTHETIC_DIR, "passengers.csv")

    if os.path.exists(conn_path):
        features_df = build_feature_matrix(conn_path, pax_path)
        print(f"Feature matrix shape: {features_df.shape}")
        print(f"Columns: {list(features_df.columns)}")
    else:
        print("No synthetic data found. Run data/generate_synthetic_data.py first.")
