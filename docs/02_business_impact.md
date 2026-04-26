# Section 2: Business Impact

## 2.1 Cost of Missed Connections — Quantified Model

### Direct Costs per Missed Connection (European Hub, Long-Haul Context)

| Cost Component | Economy | Business Class |
|---|---|---|
| Rebooking on own metal | €80–120 | €200–400 |
| Rebooking on partner/competitor | €250–600 | €800–2,000 |
| Hotel voucher (overnight) | €120–180 | €200–350 |
| Meal vouchers | €15–30 | €30–60 |
| Ground staff handling time | €25 | €25 |
| EU261 Compensation (>3hr delay) | €250–600 | €250–600 |
| **Total per pax (median)** | **€490** | **€1,050** |

### Indirect / Soft Costs

| Cost Type | Impact |
|---|---|
| NPS damage | -12 NPS points per missed connection experience (industry benchmark) |
| Loyalty churn (Senator/frequent flyers) | €3,000–8,000 LTV per churned premium member |
| Social media amplification | Negative posts reach avg. 340 connections |
| Staff overtime | €45/hr escalation cost |
| Slot penalties (if hold causes ATC slot miss) | €500–2,000 per event |

### Hub-Level Annual Cost Estimate

```
Assumptions:
  - Hub: Frankfurt (FRA), Lufthansa primary hub
  - Daily connecting passengers: ~45,000
  - Average connection pair exposure: ~12,000 passenger-pairs/day
  - Baseline missed connection rate: 2.1% (normal ops)
  - IROP day rate: 8.5% (15% of operating days are IROP)

Calculation:
  Normal days (85% of 365): 310 days × 12,000 pairs × 2.1% = 78,120 missed/year
  IROP days  (15% of 365):   55 days × 12,000 pairs × 8.5% = 56,100 missed/year
  Total annual missed connections: ~134,220
  Weighted avg cost per miss: €620 (mix of economy + business)

  ► TOTAL ANNUAL COST: ~€83.2M at FRA alone
  ► Lufthansa Group (FRA + MUC + ZRH + VIE): ~€280–340M/year
```

---

## 2.2 Value Creation Potential

### Target: 25–35% Reduction in Missed Connections

Achievable through:
- Early prediction → proactive holding decisions (saves ~40% of borderline cases)
- Pre-arranged escorts → reduces transit time by 8–12 min
- Pre-emptive rebooking → eliminates 100% of downstream chaos cost when miss is inevitable

### Financial Impact of 30% Reduction

| Metric | Current | With System | Delta |
|---|---|---|---|
| Annual missed connections (FRA) | 134,220 | 93,954 | -40,266 |
| Annual direct cost (FRA) | €83.2M | €58.2M | **-€25M** |
| Group-wide annual savings | ~€310M | ~€217M | **-€93M** |
| NPS improvement | baseline | +4–6 pts | Quantifiable |

**Conservative first-year savings (FRA only): €18–25M** (accounting for ramp-up and partial effectiveness)

---

## 2.3 KPI Framework

### Tier 1 — Operational KPIs (Daily Tracking)

| KPI | Definition | Target | Baseline |
|---|---|---|---|
| **Connection Miss Rate** | % of at-risk connections that result in misses | < 1.5% (from 2.1%) | 2.1% |
| **Prediction Accuracy** | % of actual misses correctly flagged (Recall) | > 85% | N/A |
| **Alert Lead Time** | Avg minutes before departure alert is issued | > 45 min | ~12 min |
| **Action Conversion Rate** | % of HIGH risk alerts that trigger an action | > 70% | 0% |

### Tier 2 — Financial KPIs (Weekly/Monthly)

| KPI | Definition | Target |
|---|---|---|
| **Rebooking Cost per PAX** | Direct cost of misses / total missed pax | < €400 (from €620) |
| **EU261 Payout Rate** | EU261 compensations as % of missed connections | < 30% |
| **Hold Cost Efficiency** | Cost of holds that saved connections / total hold cost | > 3:1 ROI |

### Tier 3 — Customer KPIs (Monthly/Quarterly)

| KPI | Definition | Target |
|---|---|---|
| **Connection NPS** | NPS score for connecting journey experience | > +35 |
| **Proactive Rebook Rate** | % of inevitable misses rebooked BEFORE passenger arrives at gate | > 60% |
| **Premium Pax Protection Rate** | % of Senator/HON Circle connections saved | > 95% |

---

## 2.4 ROI Estimation Model

### Investment Side (Year 1)

| Investment Item | Cost |
|---|---|
| Data engineering & platform build | €400K |
| ML model development + validation | €150K |
| Dashboard & ops tool development | €120K |
| Integration with Amadeus/AIMS APIs | €180K |
| Change management & training | €80K |
| Infrastructure (cloud, licenses) | €90K |
| **Total Year 1 Investment** | **€1.02M** |

### Return Side (Year 1 — Conservative)

| Return Item | Value |
|---|---|
| Direct rebooking savings (30% reduction, FRA) | €18M |
| EU261 compensation reduction | €3.2M |
| Staff overtime reduction | €0.8M |
| NPS uplift → retention value (est.) | €4.5M |
| **Total Year 1 Return (FRA)** | **€26.5M** |

### ROI Summary

```
Year 1 Net Benefit:  €26.5M - €1.02M  = €25.5M
Year 1 ROI:          25.5 / 1.02      = 2,500%
Payback Period:      < 3 weeks (post-launch)
5-Year NPV (8% discount, group rollout): €340M+
```

---

## 2.5 Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Data quality / missing fields | High | High | Synthetic fallback + data governance |
| Ops resistance to alerts | Medium | High | Training + phased rollout with champions |
| Hold decisions causing downstream delays | Medium | Medium | Cost-benefit guardrails in decision engine |
| Model false positive fatigue | Medium | Medium | Tunable threshold + alert confidence scores |
| Regulatory (EU261 gaming) | Low | High | Legal review of hold decision logging |
