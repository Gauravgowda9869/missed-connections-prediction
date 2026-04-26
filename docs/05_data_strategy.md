# Section 5: Data Strategy

## 5.1 Data Requirements

### Primary Data Sources

| Dataset | Description | Real Source |
|---|---|---|
| **Flight Schedules (SSIM)** | Scheduled departure/arrival, aircraft type, route | OAG Aviation, Cirium, Amadeus |
| **OTP Data (On-Time Performance)** | Actual arrival/departure times, delay codes | Eurocontrol CODA, FlightAware API |
| **Gate Assignments** | Real-time gate allocation per flight | Airport Ops Systems (Fraport API) |
| **Gate Distance Matrix** | Walking time between any two gates | Airport authority (public maps + measured) |
| **Minimum Connection Time (MCT)** | Published MCT per passenger type and terminal combination | IATA MCT Database, airline internal |
| **Passenger Manifests / DCS** | Connecting pax count per pair, loyalty tier, passport type | Airline DCS / Amadeus Altéa |
| **Historical IROP Events** | Past missed connections for model training | Airline internal ops log |

### Open Data Sources Available Today

| Source | Data Available | URL |
|---|---|---|
| **OpenSky Network** | ADS-B flight tracking, actual arrival times | opensky-network.org |
| **Eurocontrol CODA** | Aggregate European delay statistics by airport/airline | eurocontrol.int/coda |
| **BTS (US)** | US domestic OTP with detailed delay minutes | transtats.bts.gov |
| **OurAirports** | Airport and runway data | ourairports.com |
| **FlightAware / AviationStack** | Live/historical flight data (paid tiers) | flightaware.com |

**For this project**: We use a realistic **synthetic dataset** that mirrors Lufthansa FRA hub operations.

---

## 5.2 Synthetic Dataset Design

### Table 1: `flights`

| Column | Type | Description | Example |
|---|---|---|---|
| `flight_id` | VARCHAR(12) | Unique flight identifier | LH1234 |
| `flight_number` | VARCHAR(10) | IATA flight number | LH1234 |
| `origin` | VARCHAR(3) | Origin IATA airport | MUC |
| `destination` | VARCHAR(3) | Destination IATA airport | FRA |
| `scheduled_departure` | TIMESTAMP | Scheduled departure time | 2024-03-15 07:30:00 |
| `scheduled_arrival` | TIMESTAMP | Scheduled arrival time | 2024-03-15 08:45:00 |
| `estimated_arrival` | TIMESTAMP | Real-time estimated arrival | 2024-03-15 09:02:00 |
| `actual_arrival` | TIMESTAMP | Actual arrival (post-flight) | 2024-03-15 09:05:00 |
| `delay_minutes` | INTEGER | Inbound delay in minutes | 20 |
| `gate_arrival` | VARCHAR(8) | Arrival gate | C14 |
| `aircraft_type` | VARCHAR(8) | ICAO aircraft type | A320 |
| `terminal` | VARCHAR(4) | Terminal | T1 |
| `is_international` | BOOLEAN | International flight flag | TRUE |

### Table 2: `connections`

| Column | Type | Description | Example |
|---|---|---|---|
| `connection_id` | VARCHAR(20) | Unique connection pair ID | LH1234_LH456_20240315 |
| `inbound_flight_id` | VARCHAR(12) | Inbound flight ID | LH1234 |
| `outbound_flight_id` | VARCHAR(12) | Outbound flight ID | LH456 |
| `connecting_airport` | VARCHAR(3) | Hub airport | FRA |
| `inbound_arrival_gate` | VARCHAR(8) | Inbound gate | C14 |
| `outbound_departure_gate` | VARCHAR(8) | Outbound gate | Z50 |
| `scheduled_connection_time` | INTEGER | Scheduled connection time (min) | 65 |
| `minimum_connection_time` | INTEGER | MCT for this terminal pair (min) | 30 |
| `gate_walk_minutes` | INTEGER | Estimated walk time gate-to-gate | 22 |
| `requires_passport_control` | BOOLEAN | Schengen boundary crossing | TRUE |
| `passport_overhead_minutes` | INTEGER | Est. passport/security time | 15 |

### Table 3: `passengers`

| Column | Type | Description | Example |
|---|---|---|---|
| `passenger_id` | VARCHAR(20) | Anonymized pax ID | PAX_20240315_001 |
| `connection_id` | VARCHAR(20) | Connection pair | LH1234_LH456_20240315 |
| `loyalty_tier` | VARCHAR(20) | FFP status | Senator |
| `tier_score` | INTEGER | Numeric tier weight (1–5) | 4 |
| `nationality` | VARCHAR(2) | For passport control logic | DE |
| `requires_visa` | BOOLEAN | Visa requirement flag | FALSE |
| `mobility_assistance` | BOOLEAN | Special assistance needed | FALSE |
| `seat_class` | VARCHAR(10) | Travel class | Business |

### Table 4: `risk_scores` (model output)

| Column | Type | Description | Example |
|---|---|---|---|
| `score_id` | VARCHAR(30) | Unique score event ID | SCORE_001_20240315_0930 |
| `connection_id` | VARCHAR(20) | Connection being scored | LH1234_LH456_20240315 |
| `scored_at` | TIMESTAMP | When score was generated | 2024-03-15 09:30:00 |
| `risk_score` | FLOAT | 0–100 risk score | 78.5 |
| `risk_category` | VARCHAR(10) | LOW/MEDIUM/HIGH/CRITICAL | HIGH |
| `p_miss` | FLOAT | Probability of miss (0–1) | 0.785 |
| `recommended_action` | VARCHAR(20) | Decision engine output | HOLD_FLIGHT |
| `estimated_save_value` | FLOAT | Financial value if saved (€) | 4500.0 |
| `estimated_hold_cost` | FLOAT | Cost of holding (€) | 820.0 |
| `net_benefit` | FLOAT | save_value - hold_cost | 3680.0 |

### Table 5: `outcomes`

| Column | Type | Description | Example |
|---|---|---|---|
| `outcome_id` | VARCHAR(30) | Unique outcome record | OUT_001_20240315 |
| `connection_id` | VARCHAR(20) | Connection | LH1234_LH456_20240315 |
| `action_taken` | VARCHAR(20) | What ops did | HELD_FLIGHT |
| `result` | VARCHAR(10) | CONNECTION_MADE / MISSED | CONNECTION_MADE |
| `actual_cost` | FLOAT | Actual cost incurred (€) | 820.0 |
| `alert_acknowledged_at` | TIMESTAMP | When controller ack'd alert | 2024-03-15 09:35:00 |
| `controller_id` | VARCHAR(10) | Who actioned it | OPS_K_BRAUN |

---

## 5.3 Data Generation Parameters

The synthetic data generator (`data/generate_synthetic_data.py`) uses these parameters:

```python
HUB = "FRA"
SIMULATION_DAYS = 90
DAILY_CONNECTIONS = 800  # connection pairs per day at FRA
BASELINE_MISS_RATE = 0.021  # 2.1% normal ops
IROP_DAY_PROBABILITY = 0.15  # 15% of days are disrupted
IROP_MISS_RATE = 0.085  # 8.5% on IROP days

DELAY_DISTRIBUTION = {
    "no_delay": 0.55,
    "minor": 0.25,    # 5–20 min
    "moderate": 0.13, # 21–60 min
    "severe": 0.07    # 61–180 min
}

GATE_DISTANCE_RANGE = (3, 35)  # minutes, min to max at FRA
MCT_BY_TERMINAL_PAIR = {
    ("T1", "T1"): 30, ("T1", "T2"): 45,
    ("T2", "T1"): 45, ("T2", "T2"): 35,
}
```
