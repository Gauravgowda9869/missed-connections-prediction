"""
ConnectGuard — Operations Dashboard
=====================================
Streamlit dashboard for airline operations teams.
Displays real-time connection risk scores, alerts, and recommendations.

Usage:
    streamlit run src/dashboard/app.py

Author: ConnectGuard Team
"""

import os
import sys
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np
import streamlit as st

# Ensure src is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ─────────────────────────────────────────────
# PAGE CONFIGURATION
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="ConnectGuard — FRA Hub",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    /* Import fonts */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

    /* Root overrides */
    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    /* Header bar */
    .main-header {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a3e 100%);
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        border-left: 4px solid #FFD700;
    }

    /* KPI cards */
    .kpi-card {
        background: white;
        border-radius: 8px;
        padding: 1.2rem;
        border-top: 3px solid;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        text-align: center;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 700;
        line-height: 1;
        font-family: 'IBM Plex Mono', monospace;
    }
    .kpi-label {
        font-size: 0.78rem;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.4rem;
    }

    /* Risk badges */
    .badge-critical { background:#FF3B30; color:white; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
    .badge-high     { background:#FF9500; color:white; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
    .badge-medium   { background:#FFCC00; color:#333;  padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }
    .badge-low      { background:#34C759; color:white; padding:2px 10px; border-radius:12px; font-size:0.75rem; font-weight:600; }

    /* Alert box */
    .alert-box {
        background: #FFF3CD;
        border-left: 4px solid #FF9500;
        padding: 0.8rem 1rem;
        border-radius: 4px;
        margin: 0.5rem 0;
    }
    .alert-critical {
        background: #FFE5E5;
        border-left-color: #FF3B30;
    }

    /* Section headers */
    .section-header {
        font-size: 1rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #1a1a3e;
        border-bottom: 2px solid #FFD700;
        padding-bottom: 4px;
        margin-bottom: 1rem;
    }

    /* Hide Streamlit default footer */
    footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# DATA LOADING (WITH DEMO FALLBACK)
# ─────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data():
    """
    Load synthetic data if available, otherwise generate demo data in memory.
    """
    synthetic_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "synthetic")
    conn_path     = os.path.join(synthetic_dir, "connections.csv")
    risk_path     = os.path.join(synthetic_dir, "risk_scores.csv")
    out_path      = os.path.join(synthetic_dir, "outcomes.csv")

    if all(os.path.exists(p) for p in [conn_path, risk_path, out_path]):
        connections = pd.read_csv(conn_path)
        risk_scores = pd.read_csv(risk_path)
        outcomes    = pd.read_csv(out_path)
        # Use most recent day as "today"
        if "date" in connections.columns:
            latest_date = pd.to_datetime(connections["date"]).max()
            connections = connections[pd.to_datetime(connections["date"]) == latest_date]
            risk_scores = risk_scores[risk_scores["connection_id"].isin(connections["connection_id"])]
            outcomes    = outcomes[outcomes["connection_id"].isin(connections["connection_id"])]
        return connections, risk_scores, outcomes
    else:
        return _generate_demo_data()


def _generate_demo_data():
    """Generate in-memory demo data when synthetic CSVs not available."""
    random.seed(42)
    np.random.seed(42)

    n = 120  # connections for today
    inbound_flights  = [f"LH{random.randint(100,999)}" for _ in range(n)]
    outbound_flights = [f"LH{random.randint(100,999)}" for _ in range(n)]
    terminals_in  = random.choices(["T1", "T2"], k=n)
    terminals_out = random.choices(["T1", "T2"], k=n)

    gates_t1 = [f"{letter}{num}" for letter in ["A","B","C"] for num in range(1,15)]
    gates_t2 = [f"{letter}{num}" for letter in ["D","E","Z"] for num in [50,51,52,55,60,65]]

    conn_ids  = [f"{inb}_{out}_today_{i}" for i, (inb, out) in enumerate(zip(inbound_flights, outbound_flights))]
    delays    = np.random.choice([0,0,0,0,5,10,15,20,30,45,60,90], size=n, p=[0.3,0.1,0.08,0.07,0.1,0.08,0.07,0.06,0.05,0.04,0.03,0.02])
    conn_time = np.random.randint(40, 130, n)
    walk_time = np.random.randint(3, 35, n)
    mct       = np.where(np.array(terminals_in) == np.array(terminals_out), 30, 45)

    connections = pd.DataFrame({
        "connection_id":              conn_ids,
        "inbound_flight_id":          inbound_flights,
        "outbound_flight_id":         outbound_flights,
        "outbound_destination":       random.choices(["JFK","NRT","DXB","GRU","JNB","LAX","HKG","BOM"], k=n),
        "inbound_terminal":           terminals_in,
        "outbound_terminal":          terminals_out,
        "inbound_arrival_gate":       [random.choice(gates_t1 if t == "T1" else gates_t2) for t in terminals_in],
        "outbound_departure_gate":    [random.choice(gates_t1 if t == "T1" else gates_t2) for t in terminals_out],
        "inbound_delay_minutes":      delays,
        "scheduled_connection_time":  conn_time,
        "minimum_connection_time":    mct,
        "gate_walk_minutes":          walk_time,
        "requires_passport_control":  np.random.choice([True, False], size=n, p=[0.6, 0.4]),
        "passport_overhead_minutes":  np.where(np.random.random(n) < 0.6, np.random.randint(10, 20, n), 0),
    })

    # Generate risk scores
    scores = []
    for i, row in connections.iterrows():
        net = row["scheduled_connection_time"] - row["inbound_delay_minutes"] - row["gate_walk_minutes"] - row["passport_overhead_minutes"]
        buf = net - row["minimum_connection_time"]
        if buf < 0: base = random.uniform(75, 100)
        elif buf < 5: base = random.uniform(55, 80)
        elif buf < 15: base = random.uniform(35, 65)
        elif buf < 30: base = random.uniform(15, 45)
        else: base = random.uniform(0, 25)
        base = max(0, min(100, base + random.gauss(0, 4)))

        cat = "CRITICAL" if base>=85 else "HIGH" if base>=65 else "MEDIUM" if base>=40 else "LOW"
        pax = random.randint(1, 15)
        time_dep = max(5, row["scheduled_connection_time"] - row["inbound_delay_minutes"])

        if base>=85 and time_dep>20 and pax>=4: action = "HOLD_FLIGHT"
        elif base>=85: action = "PRE_REBOOK"
        elif base>=65 and time_dep>15: action = "ARRANGE_ESCORT"
        elif base>=65: action = "PRE_REBOOK"
        elif base>=40: action = "MONITOR"
        else: action = "NO_ACTION"

        avg_tier = random.uniform(0.5, 4.0)
        save_val = pax * (490 + avg_tier * 80 + 0.55 * 350)
        hold_cost = random.uniform(200, 1200) if action == "HOLD_FLIGHT" else pax * 15 if action == "ARRANGE_ESCORT" else 0

        scores.append({
            "score_id":             f"SCORE_{i:04d}",
            "connection_id":        row["connection_id"],
            "scored_at":            datetime.now() - timedelta(minutes=random.randint(0, 45)),
            "risk_score":           round(base, 1),
            "risk_category":        cat,
            "p_miss":               round(base/100, 3),
            "recommended_action":   action,
            "pax_count":            pax,
            "avg_tier_score":       round(avg_tier, 1),
            "time_to_departure_min": int(time_dep),
            "estimated_save_value": round(save_val, 0),
            "estimated_hold_cost":  round(hold_cost, 0),
            "net_benefit":          round(save_val - hold_cost, 0),
        })

    risk_scores = pd.DataFrame(scores)

    # Outcomes: simulate past results
    outcomes = pd.DataFrame({
        "connection_id": conn_ids,
        "result": np.where(
            np.random.random(n) < (risk_scores["p_miss"].values * 0.3),
            "MISSED", "CONNECTION_MADE"
        ),
        "actual_cost": np.random.exponential(200, n),
    })

    return connections, risk_scores, outcomes


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

def render_sidebar():
    with st.sidebar:
        st.markdown("### ✈️ ConnectGuard")
        st.markdown("**FRA Hub Operations**")
        st.markdown("---")

        st.markdown("**Filters**")
        risk_filter = st.multiselect(
            "Risk Level",
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            default=["CRITICAL", "HIGH"],
        )
        terminal_filter = st.multiselect(
            "Terminal",
            ["T1", "T2"],
            default=["T1", "T2"],
        )
        min_pax = st.slider("Min Pax Count", 1, 20, 1)

        st.markdown("---")
        st.markdown("**View**")
        page = st.radio(
            "Page",
            ["🏠 Hub Overview", "📋 Connection List", "📊 Analytics", "⚙️ Settings"],
            label_visibility="collapsed",
        )

        st.markdown("---")
        st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

    return risk_filter, terminal_filter, min_pax, page


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────

def render_header():
    st.markdown("""
    <div class="main-header">
        <div>
            <div style="font-size:1.4rem; font-weight:700; letter-spacing:0.02em;">
                ✈️ ConnectGuard — Frankfurt Hub
            </div>
            <div style="font-size:0.85rem; opacity:0.8; margin-top:2px;">
                Missed Connection Prediction & Decision Intelligence System
            </div>
        </div>
        <div style="margin-left:auto; text-align:right; font-family:'IBM Plex Mono',monospace; font-size:0.85rem; opacity:0.9;">
            {} UTC
        </div>
    </div>
    """.format(datetime.utcnow().strftime("%Y-%m-%d %H:%M")), unsafe_allow_html=True)


# ─────────────────────────────────────────────
# KPI TILES
# ─────────────────────────────────────────────

def render_kpis(risk_scores: pd.DataFrame, outcomes: pd.DataFrame):
    total         = len(risk_scores)
    critical_count = len(risk_scores[risk_scores["risk_category"] == "CRITICAL"])
    high_count     = len(risk_scores[risk_scores["risk_category"] == "HIGH"])
    missed_count   = len(outcomes[outcomes["result"] == "MISSED"])
    miss_rate      = missed_count / total * 100 if total > 0 else 0
    total_save_val = risk_scores["estimated_save_value"].sum()
    avg_risk       = risk_scores["risk_score"].mean()

    c1, c2, c3, c4, c5, c6 = st.columns(6)

    with c1:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#0a0a1a">
            <div class="kpi-value" style="color:#0a0a1a">{total}</div>
            <div class="kpi-label">Active Connections</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#FF3B30">
            <div class="kpi-value" style="color:#FF3B30">{critical_count}</div>
            <div class="kpi-label">Critical Alerts</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#FF9500">
            <div class="kpi-value" style="color:#FF9500">{high_count}</div>
            <div class="kpi-label">High Risk</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        color = "#FF3B30" if miss_rate > 3 else "#FF9500" if miss_rate > 1.5 else "#34C759"
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:{color}">
            <div class="kpi-value" style="color:{color}">{miss_rate:.1f}%</div>
            <div class="kpi-label">Miss Rate Today</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#34C759">
            <div class="kpi-value" style="color:#34C759">€{total_save_val/1000:.0f}K</div>
            <div class="kpi-label">Potential Savings</div>
        </div>""", unsafe_allow_html=True)
    with c6:
        st.markdown(f"""
        <div class="kpi-card" style="border-top-color:#007AFF">
            <div class="kpi-value" style="color:#007AFF">{avg_risk:.0f}</div>
            <div class="kpi-label">Avg Risk Score</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ACTIVE ALERTS TABLE
# ─────────────────────────────────────────────

RISK_COLORS = {
    "CRITICAL": "#FF3B30",
    "HIGH":     "#FF9500",
    "MEDIUM":   "#FFCC00",
    "LOW":      "#34C759",
}

ACTION_ICONS = {
    "HOLD_FLIGHT":    "🛑",
    "ARRANGE_ESCORT": "🏃",
    "PRE_REBOOK":     "🔁",
    "MONITOR":        "👁️",
    "NO_ACTION":      "✅",
}


def render_alerts(risk_scores: pd.DataFrame, connections: pd.DataFrame, risk_filter: list, terminal_filter: list, min_pax: int):
    st.markdown('<div class="section-header">⚠️ Active Alerts</div>', unsafe_allow_html=True)

    # Merge for display
    merged = risk_scores.merge(
        connections[["connection_id", "inbound_flight_id", "outbound_flight_id",
                     "outbound_destination", "inbound_terminal", "outbound_terminal",
                     "inbound_arrival_gate", "outbound_departure_gate", "inbound_delay_minutes"]],
        on="connection_id", how="left"
    )

    # Apply filters
    filtered = merged[
        (merged["risk_category"].isin(risk_filter)) &
        (merged.get("inbound_terminal", "T1").isin(terminal_filter) if "inbound_terminal" in merged.columns else True) &
        (merged["pax_count"] >= min_pax)
    ].sort_values("risk_score", ascending=False)

    if len(filtered) == 0:
        st.info("No alerts match the current filter criteria.")
        return

    # Show top 20
    for _, row in filtered.head(20).iterrows():
        cat   = row.get("risk_category", "LOW")
        color = RISK_COLORS.get(cat, "#888")
        icon  = ACTION_ICONS.get(row.get("recommended_action", "NO_ACTION"), "")
        inb   = row.get("inbound_flight_id", "???")
        out   = row.get("outbound_flight_id", "???")
        dest  = row.get("outbound_destination", "???")
        delay = row.get("inbound_delay_minutes", 0)
        pax   = int(row.get("pax_count", 0))
        score = float(row.get("risk_score", 0))
        gate_in  = row.get("inbound_arrival_gate", "?")
        gate_out = row.get("outbound_departure_gate", "?")
        term_in  = row.get("inbound_terminal", "T?")
        term_out = row.get("outbound_terminal", "T?")
        t2d      = int(row.get("time_to_departure_min", 0))
        save_val = float(row.get("estimated_save_value", 0))
        action   = row.get("recommended_action", "NO_ACTION")

        col1, col2, col3, col4, col5 = st.columns([2.5, 2, 1.5, 2, 2])
        with col1:
            st.markdown(f"""
            <div style="background:{color}15; border-left:3px solid {color}; padding:8px 12px; border-radius:4px;">
                <strong style="font-size:0.95rem;">{inb} → {out}</strong>
                <span style="color:#666; font-size:0.8rem;"> → {dest}</span>
                <br><span style="font-size:0.78rem; color:#888;">{term_in} gate {gate_in} → {term_out} gate {gate_out}</span>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            badge_cls = f"badge-{cat.lower()}"
            st.markdown(f"""
            <div style="padding-top:8px;">
                <span class="{badge_cls}">{cat}</span>
                <strong style="font-size:1.2rem; margin-left:8px; font-family:'IBM Plex Mono',monospace;">{score:.0f}</strong>
                <span style="color:#888; font-size:0.78rem;">/100</span>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div style="padding-top:8px; text-align:center;">
                <div style="font-size:1rem; font-weight:600; color:{'#FF3B30' if delay>30 else '#FF9500' if delay>10 else '#888'}">
                    +{delay} min
                </div>
                <div style="font-size:0.72rem; color:#888;">{pax} pax · {t2d}min to dep</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div style="padding-top:8px;">
                <div style="font-size:0.85rem;">{icon} <strong>{action.replace('_',' ')}</strong></div>
                <div style="font-size:0.72rem; color:#888;">Save est: €{save_val:,.0f}</div>
            </div>
            """, unsafe_allow_html=True)
        with col5:
            st.button(f"Acknowledge", key=f"ack_{row['connection_id'][:20]}", type="secondary")

        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# ANALYTICS PAGE
# ─────────────────────────────────────────────

def render_analytics(risk_scores: pd.DataFrame, outcomes: pd.DataFrame):
    st.markdown('<div class="section-header">📊 Analytics & Model Performance</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Distribution")
        cat_counts = risk_scores["risk_category"].value_counts().reindex(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"], fill_value=0
        )
        st.bar_chart(cat_counts)

    with col2:
        st.subheader("Recommended Actions")
        action_counts = risk_scores["recommended_action"].value_counts()
        st.bar_chart(action_counts)

    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Risk Score Distribution")
        hist_data = pd.cut(risk_scores["risk_score"], bins=10).value_counts().sort_index()
        st.bar_chart(hist_data)

    with col4:
        st.subheader("Potential Savings by Risk Category")
        savings = risk_scores.groupby("risk_category")["estimated_save_value"].sum().reindex(
            ["CRITICAL", "HIGH", "MEDIUM", "LOW"], fill_value=0
        )
        st.bar_chart(savings)

    st.markdown("---")
    st.subheader("📈 Key Metrics Summary")

    metrics_data = {
        "Metric": [
            "Total connections today",
            "High/Critical alerts",
            "Alert rate",
            "Average risk score",
            "Avg pax per connection",
            "Total potential savings",
            "Connections requiring hold",
            "Connections requiring escort",
        ],
        "Value": [
            f"{len(risk_scores):,}",
            f"{len(risk_scores[risk_scores['risk_category'].isin(['CRITICAL','HIGH'])]):,}",
            f"{len(risk_scores[risk_scores['risk_category'].isin(['CRITICAL','HIGH'])])/len(risk_scores)*100:.1f}%",
            f"{risk_scores['risk_score'].mean():.1f}",
            f"{risk_scores['pax_count'].mean():.1f}",
            f"€{risk_scores['estimated_save_value'].sum():,.0f}",
            f"{len(risk_scores[risk_scores['recommended_action']=='HOLD_FLIGHT']):,}",
            f"{len(risk_scores[risk_scores['recommended_action']=='ARRANGE_ESCORT']):,}",
        ]
    }
    st.dataframe(pd.DataFrame(metrics_data), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# SETTINGS PAGE
# ─────────────────────────────────────────────

def render_settings():
    st.markdown('<div class="section-header">⚙️ System Configuration</div>', unsafe_allow_html=True)
    st.markdown("**Alert Thresholds**")
    col1, col2 = st.columns(2)
    with col1:
        st.slider("CRITICAL threshold", 70, 95, 85, key="crit_thresh")
        st.slider("HIGH threshold", 50, 80, 65, key="high_thresh")
    with col2:
        st.slider("MEDIUM threshold", 20, 60, 40, key="med_thresh")
        st.slider("Min pax for HOLD recommendation", 1, 10, 4, key="min_hold_pax")

    st.markdown("---")
    st.markdown("**Notification Settings**")
    st.checkbox("Email alerts for CRITICAL", value=True)
    st.checkbox("Slack webhook for HIGH/CRITICAL", value=False)
    st.checkbox("Auto-escalate unacknowledged alerts (10 min)", value=True)

    st.markdown("---")
    st.markdown("**Data Sources**")
    st.info("✅ Synthetic data loaded from `data/synthetic/`")
    st.info("⚠️ Live ACARS feed: NOT connected (demo mode)")
    st.info("⚠️ Amadeus Altéa PSS: NOT connected (demo mode)")


# ─────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────

def main():
    render_header()

    # Sidebar
    risk_filter, terminal_filter, min_pax, page = render_sidebar()

    # Load data
    with st.spinner("Loading connection data..."):
        connections, risk_scores, outcomes = load_data()

    # Route to page
    if page == "🏠 Hub Overview":
        render_kpis(risk_scores, outcomes)
        render_alerts(risk_scores, connections, risk_filter, terminal_filter, min_pax)

    elif page == "📋 Connection List":
        st.markdown('<div class="section-header">📋 All Active Connections</div>', unsafe_allow_html=True)
        display_cols = [
            "connection_id", "risk_score", "risk_category", "p_miss",
            "recommended_action", "pax_count", "avg_tier_score",
            "time_to_departure_min", "estimated_save_value", "net_benefit"
        ]
        available_cols = [c for c in display_cols if c in risk_scores.columns]

        def color_risk(val):
            colors = {"CRITICAL": "background-color: #FF3B3020", "HIGH": "background-color: #FF950020",
                      "MEDIUM": "background-color: #FFCC0020", "LOW": "background-color: #34C75920"}
            return colors.get(val, "")

        styled = (
            risk_scores[available_cols]
            .sort_values("risk_score", ascending=False)
            .style.applymap(color_risk, subset=["risk_category"])
            .format({"risk_score": "{:.1f}", "p_miss": "{:.1%}",
                     "estimated_save_value": "€{:,.0f}", "net_benefit": "€{:,.0f}"})
        )
        st.dataframe(styled, use_container_width=True, height=600)

    elif page == "📊 Analytics":
        render_analytics(risk_scores, outcomes)

    elif page == "⚙️ Settings":
        render_settings()

    # Footer
    st.markdown("---")
    st.caption("ConnectGuard v1.0 | Frankfurt Hub | Lufthansa Group | Built for Airline Operations")


if __name__ == "__main__":
    main()
