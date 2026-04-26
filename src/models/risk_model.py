"""
ConnectGuard — Risk Scoring Model
===================================
Hybrid risk model combining rule-based triggers with a gradient-boosted
classifier to predict probability of missed connections.

Architecture:
  1. Rule-based pre-filter (hard triggers: below MCT, extreme delay)
  2. XGBoost probabilistic classifier (trained on historical data)
  3. Tier-weighted adjustment layer (premium pax get intervention discount)

Author: ConnectGuard Team
"""

import os
import pickle
import warnings
from typing import Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────
# RULE-BASED LAYER
# ─────────────────────────────────────────────

class RuleBasedLayer:
    """
    Hard-coded aviation rules that override ML output in extreme cases.
    These represent domain knowledge that data alone may not capture reliably.
    """

    @staticmethod
    def apply_rules(row: dict) -> Optional[Tuple[float, str]]:
        """
        Returns (p_miss, rule_triggered) if a hard rule fires.
        Returns None if no rule applies (proceed to ML model).
        """
        buffer = row.get("connection_buffer", 0)
        delay  = row.get("inbound_delay_minutes", 0)
        walk   = row.get("gate_walk_minutes", 0)
        net    = row.get("net_connection_time", 0)
        mct    = row.get("minimum_connection_time", 30)
        passport = row.get("requires_passport_control", False)
        passport_oh = row.get("passport_overhead_minutes", 0)

        # RULE 1: Net available time is zero or negative
        if net <= 0:
            return (0.97, "RULE_NET_TIME_ZERO")

        # RULE 2: Already well below MCT with no time to recover
        if buffer < -20 and delay > 30:
            return (0.95, "RULE_DEEP_BELOW_MCT")

        # RULE 3: Gate walk alone exceeds available time
        if walk >= net:
            return (0.93, "RULE_WALK_EXCEEDS_TIME")

        # RULE 4: Passport + walk exceeds available time
        if passport and (walk + passport_oh) >= net:
            return (0.91, "RULE_PASSPORT_WALK_EXCEEDS")

        # RULE 5: Very comfortable buffer — hard cap on risk
        if buffer >= 40 and delay == 0:
            return (0.03, "RULE_COMFORTABLE_BUFFER")

        return None  # No rule triggered — proceed to ML


# ─────────────────────────────────────────────
# ML MODEL
# ─────────────────────────────────────────────

class ConnectionRiskModel:
    """
    Gradient Boosted classifier wrapped with rule-based overrides.

    Outputs:
      - p_miss:         probability of missed connection [0, 1]
      - risk_score:     scaled 0–100 risk score
      - risk_category:  LOW / MEDIUM / HIGH / CRITICAL
      - rule_triggered: string if a hard rule fired, else None
    """

    FEATURE_COLUMNS = [
        "inbound_delay_minutes",
        "scheduled_connection_time",
        "net_connection_time",
        "connection_buffer",
        "delay_ratio",
        "urgency_score",
        "gate_walk_minutes",
        "walk_fraction",
        "minimum_connection_time",
        "is_cross_terminal",
        "requires_passport_control",
        "passport_overhead_minutes",
        "pax_count",
        "avg_tier_score",
        "weighted_tier_score",
        "pct_premium",
        "has_senator",
        "has_mobility_pax",
        "pct_visa_required",
        "delay_exceeds_buffer",
        "below_mct",
        "high_pax_tight_connection",
        "departure_hour",
        "day_of_week",
        "is_weekend",
        "peak_multiplier",
        "historical_miss_rate",
    ]

    RISK_THRESHOLDS = {
        "LOW":      (0,  30),
        "MEDIUM":   (30, 65),
        "HIGH":     (65, 85),
        "CRITICAL": (85, 100),
    }

    def __init__(self, model_type: str = "gbm"):
        """
        Parameters
        ----------
        model_type : 'gbm' (Gradient Boosting), 'rf' (Random Forest), 'lr' (Logistic Regression)
        """
        self.model_type  = model_type
        self.model       = None
        self.is_trained  = False
        self.rule_layer  = RuleBasedLayer()
        self._build_model()

    def _build_model(self):
        if self.model_type == "gbm":
            clf = GradientBoostingClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.08,
                subsample=0.85,
                min_samples_leaf=20,
                random_state=42,
            )
        elif self.model_type == "rf":
            clf = RandomForestClassifier(
                n_estimators=200,
                max_depth=6,
                min_samples_leaf=15,
                class_weight="balanced",
                random_state=42,
            )
        else:
            clf = LogisticRegression(
                C=0.5,
                class_weight="balanced",
                max_iter=1000,
                random_state=42,
            )

        self.model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf",    clf),
        ])

    # ── Training ──────────────────────────────────────────────────────

    def prepare_labels(self, outcomes_df: pd.DataFrame) -> pd.Series:
        """Convert outcome results to binary labels."""
        return outcomes_df["result"].map({
            "MISSED":           1,
            "MISSED_MANAGED":   1,
            "CONNECTION_MADE":  0,
        }).fillna(0).astype(int)

    def train(
        self,
        features_df: pd.DataFrame,
        outcomes_df: pd.DataFrame,
        evaluate: bool = True,
    ) -> dict:
        """
        Train the model on historical data.

        Parameters
        ----------
        features_df : Feature matrix (must include connection_id)
        outcomes_df : Outcomes (must include connection_id and result)
        evaluate    : If True, print evaluation metrics

        Returns
        -------
        dict with training metrics
        """
        # Merge on connection_id
        merged = features_df.merge(
            outcomes_df[["connection_id", "result"]],
            on="connection_id",
            how="inner",
        )

        # Drop rows with missing features
        feature_cols = [c for c in self.FEATURE_COLUMNS if c in merged.columns]
        merged = merged.dropna(subset=feature_cols)

        X = merged[feature_cols].copy()
        y = merged["result"].map({
            "MISSED": 1, "MISSED_MANAGED": 1, "CONNECTION_MADE": 0
        }).fillna(0).astype(int)

        print(f"[Model] Training on {len(X):,} samples | Miss rate: {y.mean():.1%}")
        print(f"[Model] Features: {len(feature_cols)}")

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        self.model.fit(X_train, y_train)
        self.is_trained = True
        self._feature_cols_used = feature_cols

        if evaluate:
            metrics = self._evaluate(X_test, y_test)
            return metrics

        return {}

    def _evaluate(self, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
        """Print and return evaluation metrics."""
        y_pred  = self.model.predict(X_test)
        y_proba = self.model.predict_proba(X_test)[:, 1]

        roc_auc = roc_auc_score(y_test, y_proba)
        avg_prec = average_precision_score(y_test, y_proba)

        print("\n" + "="*50)
        print("  MODEL EVALUATION")
        print("="*50)
        print(f"  ROC-AUC:           {roc_auc:.4f}")
        print(f"  Avg Precision:     {avg_prec:.4f}")
        print("\n  Classification Report (threshold=0.5):")
        print(classification_report(y_test, y_pred, target_names=["Made", "Missed"]))
        print("  Confusion Matrix:")
        cm = confusion_matrix(y_test, y_pred)
        print(f"    TN={cm[0,0]:,}  FP={cm[0,1]:,}")
        print(f"    FN={cm[1,0]:,}  TP={cm[1,1]:,}")
        print("="*50)

        # Find threshold for 85% recall
        precisions, recalls, thresholds = precision_recall_curve(y_test, y_proba)
        idx_85_recall = np.argmin(np.abs(recalls - 0.85))
        if idx_85_recall < len(thresholds):
            t_85 = thresholds[idx_85_recall]
            print(f"\n  Threshold for ~85% recall: {t_85:.3f}")
            print(f"  Precision at that threshold: {precisions[idx_85_recall]:.3f}")

        return {
            "roc_auc": roc_auc,
            "avg_precision": avg_prec,
            "n_test": len(y_test),
            "miss_rate": float(y_test.mean()),
        }

    # ── Inference ─────────────────────────────────────────────────────

    def predict_single(self, connection_features: dict) -> dict:
        """
        Score a single connection.

        Parameters
        ----------
        connection_features : dict with all required feature values

        Returns
        -------
        dict with p_miss, risk_score, risk_category, recommendation
        """
        # 1. Apply rule-based layer first
        rule_result = self.rule_layer.apply_rules(connection_features)
        if rule_result is not None:
            p_miss, rule = rule_result
        elif self.is_trained:
            # 2. ML model
            feature_cols = getattr(self, "_feature_cols_used", self.FEATURE_COLUMNS)
            X = pd.DataFrame([connection_features])[
                [c for c in feature_cols if c in connection_features]
            ]
            p_miss = float(self.model.predict_proba(X)[0, 1])
            rule   = None
        else:
            # 3. Fallback: heuristic only
            p_miss = self._heuristic_score(connection_features)
            rule   = "HEURISTIC_FALLBACK"

        # Tier adjustment: premium pax slightly better at making connections
        tier_score = connection_features.get("weighted_tier_score", 1.0)
        tier_discount = min(0.08, tier_score * 0.015)
        p_miss = max(0.0, p_miss - tier_discount)

        risk_score = self._p_to_risk_score(p_miss)
        category   = self._categorize(risk_score)

        from src.decision_engine.decision_engine import DecisionEngine
        action = DecisionEngine.recommend(
            risk_score         = risk_score,
            pax_count          = connection_features.get("pax_count", 3),
            time_to_departure  = connection_features.get("time_to_departure_min", 30),
            avg_tier_score     = connection_features.get("avg_tier_score", 1.0),
        )

        return {
            "p_miss":            round(p_miss, 4),
            "risk_score":        round(risk_score, 2),
            "risk_category":     category,
            "rule_triggered":    rule,
            "recommended_action": action,
        }

    def predict_batch(self, features_df: pd.DataFrame) -> pd.DataFrame:
        """
        Score a batch of connections. Faster than row-by-row for large datasets.
        """
        results = []
        for _, row in features_df.iterrows():
            result = self.predict_single(row.to_dict())
            result["connection_id"] = row.get("connection_id", "unknown")
            results.append(result)
        return pd.DataFrame(results)

    # ── Utilities ─────────────────────────────────────────────────────

    def _heuristic_score(self, f: dict) -> float:
        """Simple heuristic fallback when model is untrained."""
        buffer = f.get("connection_buffer", 0)
        delay  = f.get("inbound_delay_minutes", 0)

        if buffer < 0:    return 0.90
        elif buffer < 5:  return 0.75
        elif buffer < 15: return 0.50
        elif buffer < 30: return 0.25
        else:             return 0.05

    @staticmethod
    def _p_to_risk_score(p_miss: float) -> float:
        """Map probability to 0–100 risk score."""
        return round(min(100.0, max(0.0, p_miss * 100.0)), 2)

    @staticmethod
    def _categorize(risk_score: float) -> str:
        if risk_score < 30:  return "LOW"
        elif risk_score < 65: return "MEDIUM"
        elif risk_score < 85: return "HIGH"
        else:                 return "CRITICAL"

    def feature_importance(self) -> Optional[pd.DataFrame]:
        """Return feature importance if model supports it."""
        if not self.is_trained:
            return None
        clf = self.model.named_steps["clf"]
        if hasattr(clf, "feature_importances_"):
            cols = getattr(self, "_feature_cols_used", self.FEATURE_COLUMNS)
            return (
                pd.DataFrame({
                    "feature":    cols,
                    "importance": clf.feature_importances_,
                })
                .sort_values("importance", ascending=False)
                .reset_index(drop=True)
            )
        return None

    # ── Persistence ───────────────────────────────────────────────────

    def save(self, path: str):
        """Serialize model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)
        print(f"[Model] Saved to {path}")

    @classmethod
    def load(cls, path: str) -> "ConnectionRiskModel":
        """Deserialize model from disk."""
        with open(path, "rb") as f:
            model = pickle.load(f)
        print(f"[Model] Loaded from {path}")
        return model


# ─────────────────────────────────────────────
# STANDALONE TRAINING SCRIPT
# ─────────────────────────────────────────────

def train_from_synthetic_data(
    data_dir: str = "data/synthetic",
    model_output: str = "models/risk_model.pkl",
):
    """End-to-end training from synthetic data."""
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.data_pipeline.feature_engineering import FeatureEngineer

    print("[ConnectGuard] Training pipeline starting...")

    # Load data
    conn_path = os.path.join(data_dir, "connections.csv")
    pax_path  = os.path.join(data_dir, "passengers.csv")
    out_path  = os.path.join(data_dir, "outcomes.csv")

    for p in [conn_path, pax_path, out_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing: {p} — run data/generate_synthetic_data.py first")

    connections_df = pd.read_csv(conn_path)
    passengers_df  = pd.read_csv(pax_path)
    outcomes_df    = pd.read_csv(out_path)

    # Feature engineering
    fe = FeatureEngineer()
    features_df = fe.build_features(connections_df, passengers_df)

    # Train
    model = ConnectionRiskModel(model_type="gbm")
    metrics = model.train(features_df, outcomes_df, evaluate=True)

    # Feature importance
    fi = model.feature_importance()
    if fi is not None:
        print("\n  Top 10 Features by Importance:")
        print(fi.head(10).to_string(index=False))

    # Save
    os.makedirs(os.path.dirname(model_output), exist_ok=True)
    model.save(model_output)

    return model, metrics


if __name__ == "__main__":
    train_from_synthetic_data()
