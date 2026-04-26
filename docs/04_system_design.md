# Section 4: System Design

## 4.1 High-Level Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                     CONNECTGUARD ARCHITECTURE                    ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║  DATA SOURCES              INGESTION LAYER                       ║
║  ┌──────────────┐         ┌───────────────────────────────┐     ║
║  │ Flight OTP   │──REST──►│                               │     ║
║  │ (ATC/ACARS)  │         │    Apache Kafka / Event Bus   │     ║
║  ├──────────────┤         │    (streaming flight events)  │     ║
║  │ Schedule DB  │──SQL───►│                               │     ║
║  │ (SSIM/OAG)   │         └───────────────┬───────────────┘     ║
║  ├──────────────┤                         │                      ║
║  │ Gate Matrix  │──CSV───►┌───────────────▼───────────────┐     ║
║  │ (Airport Ops)│         │                               │     ║
║  ├──────────────┤         │    FEATURE ENGINEERING        │     ║
║  │ Pax Manifest │──API───►│    (Python / Spark)           │     ║
║  │ (PSS/DCS)    │         │    - Time to departure        │     ║
║  └──────────────┘         │    - Gate walk time           │     ║
║                           │    - Delay propagation        │     ║
║                           │    - Pax tier / count         │     ║
║                           └───────────────┬───────────────┘     ║
║                                           │                      ║
║  ┌────────────────────────────────────────▼─────────────────┐   ║
║  │                  PREDICTION ENGINE                        │   ║
║  │  ┌──────────────────┐    ┌────────────────────────────┐  │   ║
║  │  │  Risk Scorer     │    │  XGBoost / Rule-Hybrid     │  │   ║
║  │  │  (per pax pair)  │───►│  P(miss) = f(delay,dist,   │  │   ║
║  │  │                  │    │   MCT, tier, time_of_day)  │  │   ║
║  │  └──────────────────┘    └────────────────────────────┘  │   ║
║  └─────────────────────────────────┬────────────────────────┘   ║
║                                    │                             ║
║  ┌─────────────────────────────────▼────────────────────────┐   ║
║  │                  DECISION ENGINE                          │   ║
║  │  P(miss) + Cost Model + Downstream Impact                 │   ║
║  │  ──────────────────────────────────────────               │   ║
║  │  → HOLD FLIGHT      (high pax count, low downstream)     │   ║
║  │  → ARRANGE ESCORT   (medium risk, time still exists)     │   ║
║  │  → PRE-REBOOK       (CRITICAL, inevitable miss)          │   ║
║  │  → MONITOR          (LOW risk, no action yet)            │   ║
║  └─────────────────────────────────┬────────────────────────┘   ║
║                                    │                             ║
║       ┌────────────────────────────┼────────────────────────┐   ║
║       ▼                            ▼                        ▼   ║
║  ┌─────────┐              ┌──────────────┐         ┌──────────┐ ║
║  │ Ops     │              │  Alert API   │         │ Reports  │ ║
║  │Dashboard│              │  (webhook/   │         │ Service  │ ║
║  │(Streamlit│             │   push notif)│         │(daily PDF│ ║
║  └─────────┘              └──────────────┘         └──────────┘ ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 4.2 Component Details

### Component 1: Data Ingestion Layer

**Responsibility**: Collect and normalize data from multiple source systems  
**Technology**: Apache Kafka (streaming) + Airflow (batch scheduling)

| Data Feed | Type | Frequency | Source |
|---|---|---|---|
| Flight delays (ACARS) | Streaming | Real-time | Airport/ATC |
| Schedule data (SSIM) | Batch | Daily | OAG / Amadeus |
| Gate assignments | Semi-real-time | On change | Airport Ops |
| Passenger manifest | Batch | Per flight | DCS (check-in) |
| MCT matrix | Static | Weekly | Airline Network Planning |
| Gate distance matrix | Static | Monthly | Airport Authority |

**Failure Handling**: If live delay stream fails, system falls back to last known delay + 5-minute degradation warning on dashboard.

---

### Component 2: Feature Engineering Pipeline

**Responsibility**: Transform raw data into model-ready features per connection pair  
**Technology**: PySpark / Pandas (batch), Python streaming consumer (real-time)

**Key Feature Transformations**:
```python
# Per connection pair: (inbound_flight, outbound_flight, passenger_count, pax_tier)

time_to_departure   = outbound_std - current_time           # minutes
inbound_delay       = acars_estimated_arrival - inbound_sched  # minutes
time_available      = time_to_departure - inbound_delay - taxi_deplane  # net minutes
gate_walk_minutes   = gate_distance_matrix[inbound_gate][outbound_gate]
passport_overhead   = 15 if crossing_schengen else 0
net_connection_time = time_available - gate_walk_minutes - passport_overhead
connection_buffer   = net_connection_time - minimum_connection_time
risk_input_vector   = [connection_buffer, inbound_delay, pax_count, pax_tier_score,
                       time_of_day, day_of_week, route_historical_miss_rate]
```

---

### Component 3: Prediction Engine

**Model**: Hybrid Rule + Gradient Boosted Tree  
**Technology**: XGBoost (primary), rule-based override layer

**Model Training**:
- Historical IROP data (12 months minimum)
- Label: `did_miss_connection` (binary)
- Features: see Section 6

**Output**: `P(miss)` ∈ [0, 1] → mapped to risk score 0–100

**Update Cadence**: Model retrained monthly; scores updated every 5 min per connection pair

---

### Component 4: Decision Engine

**Responsibility**: Convert P(miss) → ranked action recommendations  
**Technology**: Python rule engine with cost model

Decision tree:
```
IF P(miss) > 0.85 AND time_to_departure > 20min AND pax_count > 5:
    → HOLD FLIGHT (+ cost-benefit display)
ELIF P(miss) > 0.65 AND time_available > 10min:
    → ARRANGE ESCORT (cart/fast-track)
ELIF P(miss) > 0.85 AND time_to_departure < 15min:
    → PRE-REBOOK NOW
ELIF P(miss) > 0.40:
    → MONITOR (re-evaluate in 10 min)
ELSE:
    → LOW RISK (no action)
```

**Cost Model**:
```
hold_cost       = delay_minutes × cost_per_minute × downstream_flights_affected
rebook_cost     = pax_count × avg_rebook_cost_per_pax
escort_cost     = pax_count × escort_cost_per_pax (≈ €15)
benefit_of_save = pax_count × (avg_rebook_cost + EU261_probability × EU261_amount)
```

---

### Component 5: Dashboard (Product Layer)

**Technology**: Streamlit (MVP) → React/TypeScript (production)  
**Users**: Ops Controllers (primary), Gate Agents (secondary)

Screens:
1. **Hub Overview** — Risk heatmap by terminal, KPI tiles, active alert count
2. **Connection List** — Sortable table of all active high-risk connections
3. **Connection Detail** — Single connection drill-down with recommendation + cost model
4. **Analytics** — Historical trends, model performance, savings tracker

---

## 4.3 Data Flow

```
T-90min:  Schedule data → Feature engineering → Baseline risk score (batch)
T-45min:  ACARS delay update → Re-score → Alert if HIGH risk
T-30min:  Gate assignment confirmed → Re-score with walk time
T-15min:  Final delay update → CRITICAL assessment → Hold/rebook decision
T-5min:   Last check — CRITICAL alerts escalated
T+0:      Outcome logged (miss/save) → Model feedback loop
```

---

## 4.4 Real-Time vs. Batch Considerations

| Processing Mode | Use Case | Latency Target |
|---|---|---|
| **Streaming** | Delay updates, gate changes | < 30 seconds |
| **Micro-batch** | Risk re-scoring all active pairs | Every 5 minutes |
| **Batch** | Schedule loading, model retraining | Daily/Monthly |
| **On-demand** | Controller-triggered re-score | < 5 seconds |

---

## 4.5 Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| Ingestion | Apache Kafka | Industry standard for event streaming |
| Orchestration | Apache Airflow | Mature, schedulable DAGs |
| Processing | PySpark / Pandas | Scale for batch; flexibility for dev |
| Storage | PostgreSQL (operational), S3 (historical) | Cost-effective separation |
| ML | XGBoost + scikit-learn | Fast, interpretable, production-ready |
| API | FastAPI | High-performance Python REST |
| Dashboard | Streamlit (MVP) | Fast to build; ops-friendly |
| Infrastructure | AWS (ECS + RDS + S3) | Standard enterprise cloud |
| Monitoring | Prometheus + Grafana | ML drift + system health |
