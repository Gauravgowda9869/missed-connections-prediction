import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(
    page_title="ConnectGuard | FRA Operations Control",
    page_icon="✈️",
    layout="wide"
)

# -----------------------------
# Sample data fallback
# Replace this with your real CSV/model output
# -----------------------------
alerts = pd.DataFrame([
    {
        "connection": "LH214 → LH894",
        "destination": "BOM",
        "route": "T2 Gate D65 → T1 Gate A1",
        "risk": 100,
        "risk_level": "CRITICAL",
        "delay": "+60 min",
        "pax": 11,
        "time_to_departure": 41,
        "recommendation": "HOLD FLIGHT",
        "save_estimate": 9764,
        "do_nothing_cost": 12300,
        "escort_value": 6200,
        "reason_1": "Delay exceeds buffer by 18 minutes",
        "reason_2": "Cross-terminal transfer required",
        "reason_3": "11 passengers affected",
        "propagation_risk": "LOW",
    },
    {
        "connection": "LH703 → LH697",
        "destination": "LAX",
        "route": "T1 Gate C14 → T2 Gate E52",
        "risk": 100,
        "risk_level": "CRITICAL",
        "delay": "+45 min",
        "pax": 2,
        "time_to_departure": 48,
        "recommendation": "PRE-REBOOK",
        "save_estimate": 1708,
        "do_nothing_cost": 2600,
        "escort_value": 900,
        "reason_1": "Available transfer window is below MCT",
        "reason_2": "Long gate walking time",
        "reason_3": "Low passenger count makes holding inefficient",
        "propagation_risk": "MEDIUM",
    },
    {
        "connection": "LH532 → LH422",
        "destination": "LAX",
        "route": "T1 Gate B3 → T2 Gate D52",
        "risk": 100,
        "risk_level": "CRITICAL",
        "delay": "+0 min",
        "pax": 9,
        "time_to_departure": 63,
        "recommendation": "HOLD FLIGHT",
        "save_estimate": 7667,
        "do_nothing_cost": 9800,
        "escort_value": 5400,
        "reason_1": "Gate transfer complexity is high",
        "reason_2": "Passenger volume is significant",
        "reason_3": "Premium passenger share increases service risk",
        "propagation_risk": "LOW",
    },
])

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
}

.hero {
    background: linear-gradient(135deg, #090923 0%, #19193d 100%);
    padding: 28px 34px;
    border-radius: 14px;
    border-left: 6px solid #FFD400;
    color: white;
    margin-bottom: 20px;
}

.hero h1 {
    margin-bottom: 4px;
    font-size: 30px;
}

.hero p {
    margin: 0;
    color: #D8D8E8;
}

.kpi-card {
    background: white;
    padding: 22px;
    border-radius: 14px;
    box-shadow: 0 3px 16px rgba(0,0,0,0.08);
    border-top: 4px solid #111827;
    text-align: center;
}

.kpi-value {
    font-size: 34px;
    font-weight: 800;
    margin-bottom: 4px;
}

.kpi-label {
    font-size: 12px;
    color: #666;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.priority-box {
    background: #fff7ed;
    border: 2px solid #fb923c;
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 22px;
}

.alert-card {
    background: white;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 14px;
    border-left: 5px solid #ef4444;
    box-shadow: 0 2px 14px rgba(0,0,0,0.07);
}

.risk-pill {
    display: inline-block;
    padding: 5px 10px;
    background: #ef4444;
    color: white;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.action-pill {
    display: inline-block;
    padding: 6px 12px;
    background: #111827;
    color: white;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
}

.reason-box {
    background: #f9fafb;
    padding: 12px;
    border-radius: 10px;
    font-size: 14px;
}

.whatif-box {
    background: #f8fafc;
    border-radius: 12px;
    padding: 14px;
    border: 1px solid #e5e7eb;
}

.section-title {
    font-size: 20px;
    font-weight: 800;
    margin-top: 18px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown("## ✈️ ConnectGuard")
st.sidebar.markdown("### FRA Hub Operations")

st.sidebar.divider()

st.sidebar.markdown("### Decision Strategy")
decision_mode = st.sidebar.radio(
    "Select operating mode",
    ["Balanced", "Customer-first", "Cost-first"],
    index=0
)

st.sidebar.markdown("### Filters")
risk_filter = st.sidebar.multiselect(
    "Risk level",
    ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
    default=["CRITICAL", "HIGH"]
)

terminal_filter = st.sidebar.multiselect(
    "Terminal",
    ["T1", "T2"],
    default=["T1", "T2"]
)

min_pax = st.sidebar.slider("Minimum passenger count", 1, 50, 1)

st.sidebar.divider()

view = st.sidebar.radio(
    "View",
    [
        "🏠 Operations Control",
        "🚨 Action Queue",
        "📈 Performance Insights",
        "🧪 Scenario Simulator",
        "⚙️ Settings"
    ]
)

# -----------------------------
# Header
# -----------------------------
now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

st.markdown(f"""
<div class="hero">
    <h1>✈️ ConnectGuard — Frankfurt Hub</h1>
    <p>Missed Connection Prediction & Decision Intelligence System</p>
    <p style="text-align:right; margin-top:-32px; font-family:monospace;">{now}</p>
</div>
""", unsafe_allow_html=True)

# -----------------------------
# KPIs
# -----------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)

kpis = [
    ("120", "Active Connections", "#111827"),
    ("31", "Critical Alerts", "#ef4444"),
    ("21", "High Risk", "#f59e0b"),
    ("19.2%", "Miss Rate Today", "#ef4444"),
    ("€845K", "Potential Savings", "#22c55e"),
    ("€312K", "Realized Savings", "#2563eb"),
]

for col, (value, label, color) in zip([k1, k2, k3, k4, k5, k6], kpis):
    with col:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-value" style="color:{color};">{value}</div>
            <div class="kpi-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

# -----------------------------
# Main views
# -----------------------------
if view == "🏠 Operations Control":
    top = alerts.sort_values(["risk", "save_estimate"], ascending=False).iloc[0]

    st.markdown('<div class="section-title">🔥 Top Priority Decision</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div class="priority-box">
        <div style="display:flex; justify-content:space-between; gap:20px;">
            <div>
                <h2 style="margin:0;">{top['connection']} → {top['destination']}</h2>
                <p style="margin:4px 0 12px 0; color:#555;">{top['route']}</p>
                <span class="risk-pill">{top['risk_level']}</span>
                <span style="font-size:28px; font-weight:800; margin-left:14px;">{top['risk']}/100</span>
            </div>
            <div style="text-align:right;">
                <div class="action-pill">{top['recommendation']}</div>
                <h3 style="margin:12px 0 0 0;">Save estimate: €{top['save_estimate']:,.0f}</h3>
                <p style="color:#555;">Decision window: {max(top['time_to_departure'] - 35, 3)} minutes remaining</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1.2, 1, 1])

    with c1:
        st.markdown("### 🧠 Why this alert?")
        st.markdown(f"""
        <div class="reason-box">
        • {top['reason_1']}<br>
        • {top['reason_2']}<br>
        • {top['reason_3']}<br>
        • Delay propagation risk: <b>{top['propagation_risk']}</b>
        </div>
        """, unsafe_allow_html=True)

    with c2:
        st.markdown("### 💰 What-if decision view")
        whatif = pd.DataFrame({
            "Action": ["Hold flight", "Do nothing", "Arrange escort"],
            "Estimated outcome": [
                f"Save €{top['save_estimate']:,.0f}",
                f"Lose €{top['do_nothing_cost']:,.0f}",
                f"Save €{top['escort_value']:,.0f}"
            ]
        })
        st.dataframe(whatif, hide_index=True, use_container_width=True)

    with c3:
        st.markdown("### 📌 Ops Summary")
        st.info(
            "31 critical alerts active. Highest concentration is cross-terminal transfer traffic. "
            "Recommended operating response: prioritize escort resources for T2 arrivals and hold only high-value outbound long-haul flights."
        )

    st.markdown('<div class="section-title">🚨 Action Required</div>', unsafe_allow_html=True)

    for _, row in alerts.iterrows():
        left, mid, right = st.columns([2.1, 1.5, 1.2])

        with left:
            st.markdown(f"""
            <div class="alert-card">
                <b>{row['connection']} → {row['destination']}</b><br>
                <span style="color:#666;">{row['route']}</span><br><br>
                <span class="risk-pill">{row['risk_level']}</span>
                <span style="font-size:24px; font-weight:800; margin-left:10px;">{row['risk']}</span><span style="color:#777;">/100</span>
            </div>
            """, unsafe_allow_html=True)

        with mid:
            st.markdown(f"""
            <div style="padding-top:20px;">
                <b style="color:#ef4444;">{row['delay']}</b><br>
                <span style="color:#666;">{row['pax']} pax · {row['time_to_departure']} min to departure</span><br>
                <span style="color:#666;">Save est: €{row['save_estimate']:,.0f}</span>
            </div>
            """, unsafe_allow_html=True)

        with right:
            st.markdown(f"""
            <div style="padding-top:18px;">
                <b>{row['recommendation']}</b>
            </div>
            """, unsafe_allow_html=True)
            st.button("Acknowledge", key=f"ack_{row['connection']}")

elif view == "🚨 Action Queue":
    st.markdown("## 🚨 Action Queue")
    st.caption("Prioritized operational queue sorted by financial impact and risk severity.")

    action_table = alerts[[
        "connection", "destination", "risk_level", "risk",
        "pax", "recommendation", "save_estimate", "time_to_departure"
    ]].copy()

    action_table["save_estimate"] = action_table["save_estimate"].apply(lambda x: f"€{x:,.0f}")
    action_table["time_to_departure"] = action_table["time_to_departure"].apply(lambda x: f"{x} min")

    st.dataframe(action_table, hide_index=True, use_container_width=True)

elif view == "📈 Performance Insights":
    st.markdown("## 📈 Performance Insights")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Alert Distribution")
        dist = pd.DataFrame({
            "Risk Level": ["Critical", "High", "Medium", "Low"],
            "Count": [31, 21, 44, 24]
        })
        st.bar_chart(dist.set_index("Risk Level"))

    with c2:
        st.markdown("### Decision Outcome Tracking")
        outcomes = pd.DataFrame({
            "Decision": ["Hold Flight", "Pre-Rebook", "Escort", "Monitor"],
            "Realized Savings": [142000, 88000, 62000, 20000]
        })
        st.bar_chart(outcomes.set_index("Decision"))

    st.markdown("### PM Interpretation")
    st.success(
        "The strongest financial impact comes from selective flight holds, but pre-rebooking provides a lower-risk alternative when the decision window is too short."
    )

elif view == "🧪 Scenario Simulator":
    st.markdown("## 🧪 Scenario Simulator")
    st.caption("Use this to demonstrate product thinking: what happens if operational conditions change?")

    delay_increase = st.slider("Increase inbound delay by minutes", 0, 60, 10)
    pax_multiplier = st.slider("Passenger volume multiplier", 1.0, 3.0, 1.2)

    simulated_risk = min(100, 52 + delay_increase * 0.9 + pax_multiplier * 8)
    estimated_loss = int(4500 + delay_increase * 180 + pax_multiplier * 1200)

    c1, c2, c3 = st.columns(3)

    c1.metric("Simulated Risk Score", f"{simulated_risk:.0f}/100")
    c2.metric("Estimated No-Action Cost", f"€{estimated_loss:,.0f}")
    c3.metric("Recommended Strategy", "Hold / Escort" if simulated_risk > 75 else "Monitor")

    st.info(
        "This simulator shows how a PM can test operational assumptions before rollout. "
        "It demonstrates trade-off thinking, not just ML prediction."
    )

else:
    st.markdown("## ⚙️ Settings")
    st.write("Configuration placeholder for data refresh frequency, alert thresholds, and decision cost assumptions.")
