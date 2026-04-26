# Section 3: Product Requirements Document (PRD)

## Overview
**Product Name**: ConnectGuard — Missed Connection Prediction & Decision Intelligence System  
**Version**: 1.0  
**Owner**: Product Management — Airline Operations Intelligence  
**Date**: 2024  
**Status**: Approved for Development

---

## 3.1 Problem & Opportunity

Airline operations teams lack a unified, probabilistic, real-time tool to predict missed connections and translate risk into actionable decisions. This PRD defines the requirements for ConnectGuard — a system that monitors every connecting passenger pair, scores connection risk in real-time, and recommends concrete interventions.

---

## 3.2 Feature Prioritization (MoSCoW)

### MUST HAVE (MVP)

| ID | Feature | Rationale |
|---|---|---|
| F01 | Real-time connection risk scoring (per pax pair) | Core value proposition |
| F02 | Alert feed for HIGH risk connections | Ops teams need actionable list |
| F03 | Decision recommendations engine | PM differentiator |
| F04 | Ops dashboard (web) | Tool ops teams will use |
| F05 | Historical miss/save tracking | Model validation + reporting |
| F06 | Integration with flight schedule data | Data foundation |

### SHOULD HAVE

| ID | Feature | Rationale |
|---|---|---|
| F07 | Passenger tier weighting (Senator/HON) | Revenue protection |
| F08 | Gate distance matrix integration | Accuracy boost |
| F09 | Cost-benefit display per hold decision | Ops buy-in |
| F10 | Shift summary report (PDF/email) | End-of-day ops review |

### COULD HAVE

| ID | Feature | Rationale |
|---|---|---|
| F11 | Mobile app for gate agents | Field usability |
| F12 | Passenger SMS/app notification | Proactive comms |
| F13 | Alternate flight pre-booking automation | Ops efficiency |
| F14 | ATC slot impact calculator for holds | Cost-benefit depth |

### WON'T HAVE (v1.0)

| ID | Feature | Rationale |
|---|---|---|
| F15 | Full PSS integration (Amadeus Altéa) | Complex; v2.0 |
| F16 | Baggage reconnection tracking | Separate system |
| F17 | Crew connection management | Different workflows |

---

## 3.3 Functional Requirements

### FR-01: Risk Scoring Engine
- **FR-01.1**: System SHALL calculate connection risk score (0–100) for every active pax-connection pair
- **FR-01.2**: Score SHALL be updated every 5 minutes (or on trigger event: gate change, delay update)
- **FR-01.3**: Risk SHALL be classified: LOW (<30), MEDIUM (30–65), HIGH (65–85), CRITICAL (>85)
- **FR-01.4**: Score SHALL incorporate: inbound delay, connection time remaining, gate distance, pax tier, terminal crossing requirement

### FR-02: Alert System
- **FR-02.1**: Alerts SHALL be issued for connections with risk score > 65
- **FR-02.2**: Alerts SHALL include: flight pair, pax count, risk score, recommended action, cost estimate
- **FR-02.3**: Ops controllers SHALL be able to acknowledge, action, or dismiss alerts
- **FR-02.4**: Unacknowledged CRITICAL alerts SHALL escalate after 10 minutes

### FR-03: Decision Recommendations
- **FR-03.1**: For HIGH/CRITICAL risk, system SHALL recommend one of: [HOLD FLIGHT | ARRANGE ESCORT | PRE-REBOOK | MONITOR]
- **FR-03.2**: Recommendation SHALL display estimated cost and pax count impacted
- **FR-03.3**: System SHALL show confidence level for each recommendation
- **FR-03.4**: Hold recommendation SHALL include estimated downstream delay impact

### FR-04: Dashboard
- **FR-04.1**: Dashboard SHALL show all active high-risk connections, updated in near real-time
- **FR-04.2**: Dashboard SHALL include a hub-level risk heatmap by terminal/time
- **FR-04.3**: Dashboard SHALL display KPI tiles: missed today, saved today, alerts actioned
- **FR-04.4**: Dashboard SHALL support filtering by: terminal, flight, risk level, pax tier

### FR-05: Reporting
- **FR-05.1**: System SHALL log all alerts, decisions, and outcomes
- **FR-05.2**: Daily ops report SHALL be auto-generated at 23:59 local hub time
- **FR-05.3**: Reports SHALL show: alert accuracy, action conversion, savings estimated

---

## 3.4 Non-Functional Requirements

| Category | Requirement |
|---|---|
| **Latency** | Risk score refresh ≤ 5 minutes; alert delivery ≤ 30 seconds |
| **Availability** | 99.9% uptime during hub operating hours (05:00–23:00 local) |
| **Scalability** | Support 500 simultaneous active connections at peak |
| **Security** | PII data (passenger names) encrypted at rest and in transit; GDPR compliant |
| **Auditability** | All decisions logged with timestamp, user, action, and outcome |
| **Resilience** | Graceful degradation: if live feed fails, system runs on last-known delay data |
| **Usability** | Dashboard usable by ops controller within 2-minute onboarding |

---

## 3.5 Constraints

| Constraint | Description |
|---|---|
| **MCT Floor** | System cannot recommend holding below airline's published Minimum Connection Time + 5 min buffer |
| **Slot Coordination** | Hold recommendations must account for ATC slot windows; holding > 20 min requires ATC notification |
| **Data Access** | Initially limited to schedule + OTP data; no live PSS integration in v1.0 |
| **Staff Authority** | System recommends; final hold decision authority remains with NOC controller |
| **EU Regulations** | EU261 liability clock starts at departure; system must log rationale for holds |
| **Airport Cooperation** | Gate distance matrix requires Fraport data-sharing agreement |

---

## 3.6 Success Metrics (6-Month Post-Launch)

| Metric | Target |
|---|---|
| Missed connection rate | Reduce from 2.1% to < 1.5% (FRA, normal ops) |
| Alert accuracy (Precision) | > 75% (of alerts raised, connection was genuinely at risk) |
| Alert recall | > 85% (of actual misses, system predicted them) |
| Alert acknowledgment rate | > 90% within 10 minutes |
| Ops controller satisfaction | > 4.2 / 5.0 (post-adoption survey) |
| System uptime | > 99.9% during operating hours |
| Proactive rebook rate | > 50% of inevitable misses rebooked before gate arrival |

---

## 3.7 Acceptance Criteria

### Epic 1: Risk Scoring
- AC: Given a flight pair with inbound delay of 25min, MCT of 30min, and gate distance of 15min — system scores risk > 70 and classifies as HIGH ✓
- AC: Score updates within 5 minutes of an ATC delay update ✓

### Epic 2: Decision Engine
- AC: For a HIGH risk with 12 transferring pax, system recommends HOLD with cost estimate displayed ✓
- AC: For a CRITICAL risk with 2 economy pax and 40-min downstream impact, system recommends PRE-REBOOK ✓

### Epic 3: Dashboard
- AC: All HIGH/CRITICAL connections visible on dashboard within 30 seconds of scoring ✓
- AC: Ops controller can filter, acknowledge, and action an alert in < 3 clicks ✓
