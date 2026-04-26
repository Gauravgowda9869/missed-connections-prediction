# Section 1: Product Thinking

## 1.1 Problem Statement

Every year, **airlines lose an estimated $3–5 billion** globally due to missed connections. At major European hubs like Frankfurt (FRA) and Munich (MUC), where Lufthansa operates hundreds of daily feeder-to-longhaul connections, the problem is systemic:

- A delayed inbound flight arrives 22 minutes late
- A connecting passenger has a 35-minute connection window (Minimum Connection Time = 30 min)
- Ground staff are not alerted proactively
- The longhaul flight departs on time
- The passenger is stranded — triggering rebooking, hotel vouchers, compensation, and NPS damage

**The problem is not that delays happen. The problem is that decisions are made too late, with too little data.**

### Quantified Scope (Lufthansa Group Assumptions)
- ~1,200 connecting flights per day at FRA hub
- ~8% average missed connection rate during IROP (Irregular Operations) days
- ~96 missed connections per disrupted day at FRA alone
- Average cost per missed connection: **€450** (rebooking + hotel + meal voucher + staff time)
- Annual cost at FRA alone: ~**€158M** (conservative estimate)

---

## 1.2 Why This Problem Exists in Aviation

The aviation connection ecosystem is extraordinarily complex. Key structural causes:

| Root Cause | Description |
|---|---|
| **Cascading delays** | A delay in Tokyo propagates to a Frankfurt connection to New York |
| **Siloed data systems** | Arrival data (OTP) lives in one system, gate assignments in another, passenger manifests in a third |
| **Reactive operations** | Ground staff learn of a tight connection when the inbound aircraft lands, not 90 minutes before |
| **MCT is a blunt instrument** | Minimum Connection Time is airport-level average, not passenger-specific (elderly, family, premium vs economy) |
| **Gate distance variance** | Gate C14 to Z50 at FRA can be 25 minutes walking; C14 to C18 is 3 minutes |
| **No prediction loop** | Decisions (hold flight, arrange escort, rebook) happen in isolation with no probability scoring |

---

## 1.3 Stakeholders

```
┌─────────────────────────────────────────────────────────────┐
│                     STAKEHOLDER MAP                         │
├──────────────────┬──────────────────────────────────────────┤
│  Airline Ops     │ Need real-time connection risk per flight │
│  Control Center  │ pair with recommended actions             │
├──────────────────┼──────────────────────────────────────────┤
│  Ground Staff /  │ Need actionable alerts: "Meet pax at      │
│  Gate Agents     │ gate C12, escort to Z50"                  │
├──────────────────┼──────────────────────────────────────────┤
│  Revenue Teams   │ Need cost-benefit analysis: is holding    │
│  / Finance       │ flight cheaper than rebooking 18 pax?     │
├──────────────────┼──────────────────────────────────────────┤
│  Passengers      │ Need proactive rebooking offers, not      │
│                  │ stranded surprises                         │
├──────────────────┼──────────────────────────────────────────┤
│  Airport Ops     │ Gate availability, bus logistics, jetway  │
│  (Fraport)       │ coordination                              │
├──────────────────┼──────────────────────────────────────────┤
│  IT / Data Eng   │ Need clean APIs, data pipelines, SLAs     │
└──────────────────┴──────────────────────────────────────────┘
```

---

## 1.4 User Personas

### Persona 1: Klaus — Airline Operations Controller
**Role**: Senior Operations Controller, Lufthansa Network Operations Control (NOC), Frankfurt  
**Age**: 44  
**Context**: Klaus manages 200+ active flights simultaneously during a disruption day. He has 3 screens, a radio, and a phone — all active at once.

**Goals**:
- Minimize total system delay propagation
- Make hold/depart decisions in < 5 minutes
- Protect high-value passengers (Senator, HON Circle members)

**Pain Points**:
- Gets connection data from 4 different tools (AIMS, WorldTracer, OPS Portal, Excel)
- No single risk score — must mentally calculate "will pax make it?"
- Hold decisions are based on gut + phone calls to gate agents
- No visibility into cascading downstream effects of holding a flight

**Quote**: *"By the time I know a connection is at risk, the gate is already closing."*

---

### Persona 2: Fatima — Gate Agent, Terminal Z
**Role**: Ground Operations Agent, Frankfurt Airport, Lufthansa hub  
**Age**: 29  
**Context**: Fatima manages 3–4 gate departures per shift. She gets calls from operations but often discovers tight connections herself when passengers run to her gate breathless.

**Goals**:
- Know 30 minutes before departure which passengers are at risk
- Have a protocol: who to hold for, who to call a cart for
- Avoid holding the entire plane for one passenger unnecessarily

**Pain Points**:
- Passenger connection data is buried in a system she rarely has time to check
- No priority list — all arriving pax are treated equally
- Escalation path is unclear: "Do I call ops? Do I just close the gate?"

**Quote**: *"I held the flight once for a passenger who was already in the lounge. I didn't know."*

---

### Persona 3: Amara — Business Traveler (Senator Card)
**Role**: Management Consultant, frequent Frankfurt hub user  
**Age**: 38  
**Context**: Amara books tight connections intentionally to maximize productivity. She expects Lufthansa to proactively manage disruptions.

**Goals**:
- Land, clear passport control quickly, board connection
- If connection is missed: get rebooked on next available before she even reaches the gate
- Clear communication, no surprises

**Pain Points**:
- Receives no proactive notification that her connection is at risk
- Discovers she's missed at the gate — no alternate booking prepared
- Customer service queue takes 45 minutes; she misses a client meeting

**Quote**: *"I pay for business class. Why am I finding out I'm stranded at the gate?"*

---

### Persona 4: Raj — Head of Revenue Management
**Role**: VP Revenue & Network Planning, Lufthansa Group  
**Age**: 51  
**Context**: Raj sees missed connections as a P&L item. Each missed connection costs money and erodes loyalty. He wants data-driven evidence to invest in prevention.

**Goals**:
- Quantify the cost of missed connections per route
- Build business case for holding decisions
- Protect high-yield passenger segments

**Pain Points**:
- No consolidated reporting on missed connections vs. revenue impact
- Can't answer: "Is it cheaper to hold or rebook?"
- No forward-looking analytics — only post-flight reporting

---

## 1.5 Passenger Journey: Landing to Connection

```
[INBOUND FLIGHT LANDS]
        │
        ▼
[TAXI TO GATE] ──── Risk window begins here
        │              Prediction should trigger
        ▼
[DEBOARD AIRCRAFT] ── Aisle position matters (exit sequence)
        │
        ▼
[WALK/TRANSIT] ──── Gate distance is KEY variable
        │              Schengen vs. non-Schengen matters hugely
        ▼
[PASSPORT/SECURITY] ── Non-EU pax add 10-25 min
        │
        ▼
[REACH CONNECTING GATE] ── Final boarding call window
        │
        ▼
[BOARD OR MISS] ──── Decision point: gate closes
```

### Pain Points by Stage

| Stage | Pain Point |
|---|---|
| Taxi to gate | No alert to ground staff; time already ticking |
| Deboard | Pax unaware they need to run; no priority disembark for tight connections |
| Walk/Transit | No escort arranged; no cart for elderly/mobility |
| Passport/Security | No fast-track arranged for tight connections |
| Connecting gate | Gate agent unaware of inbound; may have already closed |

---

## 1.6 Competitive / Industry Analysis

| Airline / Tool | Current Approach | Limitation |
|---|---|---|
| **Lufthansa NOC** | Manual ops controllers; AIMS system | Reactive, no risk scoring |
| **Delta ConnectionSaver** | Holds flights automatically for connecting pax | US domestic only; no international complexity |
| **United ConnectionMate** | Similar to Delta; app-based notifications | Limited to hub capacity |
| **Amsterdam Schiphol** | Airport-level connection assist | Reactive, not predictive |
| **SITA AMS** | Passenger processing solutions | No predictive connection analytics |
| **Amadeus Altéa** | PSS with connection logic | Rule-based MCT only, not probabilistic |

**Key insight**: Delta's ConnectionSaver (domestic US) proves the concept works. **No European carrier has built a probabilistic, multi-variable connection risk engine for international longhaul hubs.**

---

## 1.7 Opportunity Gap

The gap is clear:

1. **No real-time probability score** — only binary MCT pass/fail
2. **No passenger-level personalization** — same rules for a Senator cardholder vs. leisure economy pax
3. **No decision intelligence** — predictions exist in isolation from recommended actions
4. **No cost-benefit logic** — hold decision is not weighed against downstream delay cost
5. **No proactive passenger communication** — pax are informed after the fact

**This system fills all five gaps.**
