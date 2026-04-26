# ✈️ ConnectGuard — Missed Connection Prediction & Decision Intelligence System

> **A production-grade airline operations intelligence system that predicts the probability of passengers missing connecting flights and provides actionable recommendations to reduce missed connections and associated costs.**

## 🚀 Live Demo

👉 **[Launch ConnectGuard Dashboard](https://missed-connections-prediction-k9rerwu9qoubzusezgox3s.streamlit.app/)**

> Simulates real-time missed connection risk scoring and operational decision-making for airline hubs.

⚠️ Note: The system uses synthetic FRA hub data for demonstration purposes.

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red)](https://streamlit.io)
[![Live App](https://img.shields.io/badge/Live%20Demo-ConnectGuard-brightgreen)](https://missed-connections-prediction-k9rerwu9qoubzusezgox3s.streamlit.app/)
[![Domain](https://img.shields.io/badge/Domain-Aviation%20Ops-navy)](/)
[![Type](https://img.shields.io/badge/Type-Product%20%2B%20ML%20%2B%20System%20Design-green)](/)
---

## 🎯 Problem Statement

Every year, airlines lose **€3–5 billion globally** due to missed connections. At major European hubs like Frankfurt (FRA), where Lufthansa operates hundreds of daily feeder-to-longhaul connections:

- A delayed inbound flight arrives 22 minutes late
- A connecting passenger has a 35-minute connection window
- Ground staff are **not alerted proactively**
- The longhaul flight departs — passenger is stranded
- This triggers rebooking, hotel vouchers, EU261 compensation, and NPS damage

**The problem is not that delays happen. The problem is that decisions are made too late, with too little data.**

---
## ❗ Why This Problem Matters

Missed connections are not just passenger inconvenience — they are a **core disruption problem in airline operations**.

- Passenger connectivity is one of the most complex and least optimized areas in airline systems  
- Prediction of missed connections is still an emerging research area with limited real-world deployment :contentReference[oaicite:0]{index=0}  
- Delays propagate across the network, causing cascading operational and financial impact :contentReference[oaicite:1]{index=1}  

👉 ConnectGuard bridges the gap between **prediction and operational decision-making**, which is still missing in most systems.

---

## 🧑‍💼 Product Thinking Highlights

- Designed as a **decision-support system**, not just a prediction model  
- Translates ML outputs into **operational actions with cost trade-offs**  
- Aligns with real airline workflows (AOCC / NOC environments)  
- Balances **customer experience vs operational cost vs network impact**

---

## 💡 Solution — ConnectGuard

ConnectGuard is a **real-time prediction and decision intelligence system** that:

1. **Predicts** — Scores every connecting passenger pair with a 0–100 risk score updated every 5 minutes
2. **Recommends** — Translates risk scores into actionable decisions: Hold Flight / Arrange Escort / Pre-Rebook / Monitor
3. **Quantifies** — Shows ops teams the cost-benefit of each action in real time
4. **Learns** — Tracks outcomes to continuously improve model accuracy

---

## 💰 Business Impact

| Metric | Value |
|---|---|
| Annual cost of missed connections (FRA hub) | ~€83M |
| Target reduction | 25–35% |
| Conservative Year 1 savings (FRA) | **€18–25M** |
| Year 1 investment | €1.02M |
| ROI | **~2,500%** |
| Payback period | < 3 weeks post-launch |

---

## 🏗️ System Architecture

```
DATA SOURCES → KAFKA EVENT BUS → FEATURE ENGINEERING → PREDICTION ENGINE
                                                               ↓
                                                      DECISION ENGINE
                                                    (cost-benefit model)
                                                               ↓
                                          OPS DASHBOARD ← ALERT API → REPORTS
```

**Key Components:**
- **Data Pipeline** — Ingests flight schedules, ACARS delays, gate assignments, passenger manifests
- **Feature Engineering** — Computes net connection time, buffer, walk fractions, passenger tier weights
- **Hybrid Risk Model** — Rule-based layer + Gradient Boosted classifier → P(miss) score
- **Decision Engine** — Maps P(miss) + cost model → ranked action recommendations
- **Streamlit Dashboard** — Real-time ops view with alerts, filters, and KPI tiles

---

## 📁 Project Structure

```
missed-connections-prediction/
│
├── README.md                          ← You are here
├── requirements.txt                   ← Python dependencies
│
├── docs/
│   ├── 01_product_thinking.md         ← Problem, personas, journey, competitive analysis
│   ├── 02_business_impact.md          ← Cost model, KPIs, ROI estimation
│   ├── 03_prd.md                      ← Full Product Requirements Document
│   ├── 04_system_design.md            ← Architecture, components, data flow
│   └── 05_data_strategy.md            ← Data sources, schema, synthetic design
│
├── data/
│   ├── generate_synthetic_data.py     ← Generates realistic FRA hub simulation data
│   └── synthetic/                     ← Output CSVs (auto-generated)
│       ├── flights.csv
│       ├── connections.csv
│       ├── passengers.csv
│       ├── risk_scores.csv
│       └── outcomes.csv
│
├── src/
│   ├── data_pipeline/
│   │   └── feature_engineering.py    ← Feature computation pipeline
│   ├── models/
│   │   └── risk_model.py             ← Hybrid rule + GBM risk scorer
│   ├── decision_engine/
│   │   └── decision_engine.py        ← Action recommendations + cost-benefit
│   └── dashboard/
│       └── app.py                    ← Streamlit ops dashboard
│
└── tests/
    └── test_risk_model.py            ← Unit + integration tests
```

---

## 🚀 Quick Start

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/missed-connections-prediction.git
cd missed-connections-prediction
pip install -r requirements.txt
```

### 2. Generate synthetic data

```bash
python data/generate_synthetic_data.py
# Generates 90 days of realistic FRA hub data (~72,000 connections)
```

### 3. Launch the dashboard

```bash
streamlit run src/dashboard/app.py
```

Open `http://localhost:8501` — dashboard loads with live risk scores and alerts.

### 4. Run the decision engine demo

```bash
python src/decision_engine/decision_engine.py
```

### 5. Run tests

```bash
pytest tests/ -v
```

---

## 📊 Key Features

### Risk Scoring
- Hybrid rule-based + ML model (Gradient Boosting)
- Inputs: delay, gate walk time, MCT, Schengen crossing, passenger tier, time of day
- Output: 0–100 risk score + CRITICAL / HIGH / MEDIUM / LOW classification

### Decision Engine
| Risk Level | Action | Logic |
|---|---|---|
| CRITICAL (85+) + enough time | HOLD FLIGHT | Cost-benefit: save value > hold cost |
| CRITICAL + < 8 min window | PRE-REBOOK | Too late to hold |
| HIGH (65–85) + time available | ARRANGE ESCORT | Cart / fast-track / priority |
| MEDIUM (40–65) | MONITOR | Reassess in 10 min |
| LOW (< 40) | NO ACTION | Buffer is adequate |

### Dashboard
- Hub overview with KPI tiles (miss rate, savings potential, alert count)
- Filterable alert feed sorted by risk score
- Cost-benefit display per alert
- Analytics page with model performance metrics

---

## 📐 Data Schema

Five tables power the system:

| Table | Records (90 days) | Description |
|---|---|---|
| `flights` | ~72,000 | Inbound feeder flights with delays |
| `connections` | ~72,000 | Connection pairs with MCT, gate data |
| `passengers` | ~576,000 | Pax per connection with tier/class |
| `risk_scores` | ~72,000 | Model output per connection |
| `outcomes` | ~72,000 | Actual results (training labels) |

---

## 🧠 Model Design

```
Input Features (27 total):
  Time/Delay:    inbound_delay, net_connection_time, connection_buffer,
                 delay_ratio, urgency_score
  Gate/Route:    gate_walk_minutes, is_cross_terminal, requires_passport,
                 walk_fraction, minimum_connection_time
  Passengers:    pax_count, avg_tier_score, pct_premium, has_senator
  Temporal:      departure_hour, day_of_week, peak_multiplier
  Flags:         below_mct, delay_exceeds_buffer, high_pax_tight_connection

Model: Rule override layer → GradientBoostingClassifier → tier adjustment
Output: P(miss) ∈ [0,1] → Risk Score 0–100
```

Target metrics: **ROC-AUC > 0.85**, **Recall > 85%** at alert threshold

---

## 🗺️ Implementation Roadmap

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Product + Data | PRD, personas, synthetic data generator, schema |
| 2 | Modeling | Feature engineering, risk model, decision engine |
| 3 | Dashboard | Streamlit app, alert feed, KPI tiles |
| 4 | Refinement | Tests, documentation, README, demo recording |

---

## 🔮 Future Improvements

- **Live data integration** — ACARS feed, Amadeus Altéa PSS API
- **LLM decision rationale** — GPT-4 generates natural-language ops briefings per alert
- **Passenger-facing notifications** — Push alerts to Lufthansa app for at-risk pax
- **Baggage reconnection module** — Track bags separately from passengers
- **Multi-hub rollout** — Extend to MUC, ZRH, VIE with hub-specific MCT matrices
- **Crew connection tracking** — Different urgency model for crew vs. passengers

---

## 🤝 How Airlines Could Use This

**Lufthansa**: Deploy at FRA/MUC hubs. Integrate with existing NOC screens. Estimated €93M group-wide savings.

**Ryanair**: Adapt for tight domestic turnarounds. Alert gate agents to hold boarding for connecting pax.

**Hub airports (Fraport/Schiphol)**: White-label as airport service to all airlines operating at hub.

---

## 📄 Documentation

Full product and technical documentation in `/docs/`:

- [Product Thinking & Personas](docs/01_product_thinking.md)
- [Business Impact & ROI Model](docs/02_business_impact.md)
- [Product Requirements Document](docs/03_prd.md)
- [System Design & Architecture](docs/04_system_design.md)
- [Data Strategy & Schema](docs/05_data_strategy.md)

---

## 👤 Author

Built as a demonstration of end-to-end Product Management + Data Science + Aviation Domain expertise.

**Skills demonstrated**: Product thinking · User personas · PRD writing · System design · Feature engineering · ML modeling · Decision engine design · Business impact quantification · Dashboard development · Technical documentation

---

*This project demonstrates what a top-tier PM/DS candidate can build — from business problem to working system.*
