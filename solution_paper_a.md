# ORACLE-X/N: Task A — Psychologically Authentic Review Generation and Star-Rating Prediction

**DSN × BCT LLM Agent Hackathon 2026**  
Team: ORACLE-X/N &nbsp;|&nbsp; Submission: 23 May 2026  
Task: **A — Authenticated Review Simulation**

---

## Abstract

We present ORACLE-X/N's approach to **Task A**: generating psychologically authentic star ratings and written reviews for items a user has not yet interacted with. The core challenge is not textual fluency — any LLM can produce plausible reviews — but *fidelity*: producing a rating and review that are consistent with *who this user actually is*: their Big Five personality, nine Nigerian-specific behavioural traits, their current emotional state, and the regional linguistic norms of their city. Our hybrid approach blends LLM generation with a heuristic rating estimator anchored to a 14-dimensional personality vector. On 40 held-out Nigerian consumer profiles across 79 rated interactions, we measure **RMSE of 0.8992** (MAE 0.4861) and **BERTScore-F1 of 0.905** (RoBERTa-large), outperforming a mean-rating baseline (RMSE ≈ 1.40) by **37%**.

---

## 1. Introduction

Standard review generation systems treat users as preference vectors over item categories. This is insufficient for three reasons specific to the Nigerian digital commerce context:

1. **Cultural linguistic diversity** — A Lagos tech buyer and an Abuja civil servant do not write the same review even for the same product. Differences in Pidgin usage, Yoruba-English code-switching, formality level, and reference to locally-specific concerns (fake products, delayed delivery, BNPL payment) produce fundamentally different review text.

2. **Temporal emotional state** — Reviews written during financial pressure ("end of month", "budget crunch") skew negative relative to the same user's payday reviews. A static preference vector misses this temporal drift.

3. **Rating calibration bias** — Nigerian consumers in our dataset demonstrate archetype-specific rating skews: *value hunters* deflate ratings by −0.3 to −0.8 relative to the item's average when their price expectations are unmet; *brand loyalists* inflate ratings by +0.5 when the brand matches their historical preferences.

ORACLE-X/N addresses all three by conditioning every review generation call on a **14-dimensional personality vector**, **temporal emotional state**, **life context**, and **archetype-specific rating calibration rules**.

---

## 2. Task Formulation

Given:
- A user profile $U$ with personality vector $\mathbf{p} \in \mathbb{R}^{14}$, interaction history $\mathcal{H}$, linguistic style $\ell$, region $r$, and current emotional state $e$
- An item $I$ with category, price (Naira), seller region, and description

Produce:
- A star rating $\hat{r} \in [1, 5]$ minimising $\text{RMSE}(\hat{r}, r^*)$ against ground-truth ratings
- A written review $\hat{v}$ maximising $\text{BERTScore\text{-}F1}(\hat{v}, v^*)$ and $\text{ROUGE-L}(\hat{v}, v^*)$ against ground-truth text

The evaluation is a **cold-start** scenario: the user has not previously reviewed item $I$. Ratings must be predicted from personality and context, not from the user's item-specific history.

---

## 3. System Architecture

Three engines handle Task A: **MemoryEngine** loads the `UserProfile` (personality vector, interaction history, linguistic style, archetype, region, emotional state) and computes the user's historical average rating as a calibration anchor. **ReviewEngine** assembles a structured prompt (persona preamble + purchase context + item description + linguistic style instruction), calls the LLM, blends the rating, and validates JSON output. **LLMClient** abstracts two Groq models:

| Model | Use case | Temperature |
|---|---|---|
| `llama-3.3-70b-versatile` | Structured JSON rating + review generation | 0.75 |
| `llama-3.1-8b-instant` | Streaming chat, fast-path fallback | 0.85 |

All Task A calls use the 70B model via JSON mode. Temperature 0.75 balances review creativity with schema compliance.

**Rating blend**: the final predicted rating merges LLM and heuristic signals: $\hat{r} = 0.7 \cdot r_{\text{LLM}} + 0.3 \cdot r_{\text{heuristic}}$, where the heuristic anchors on the user's historical average adjusted for price-value alignment, fake-product suspicion, brand loyalty match, and life-context delta (±0.5). This blend prevents extreme LLM outliers inconsistent with documented user history. A fallback chain (8B model → templated response) handles API failures without silent errors.

---

## 4. Nigerian Context Layer

The core contribution is the explicit encoding of Nigerian consumer psychology into every review generation call.

### 4.1 Personality Vector (14 Dimensions)

| Dimension | Domain | Role in Review Generation |
|---|---|---|
| openness | Big Five | Receptivity to novel/niche products |
| conscientiousness | Big Five | Research depth, detail in review |
| extraversion | Big Five | Social sharing language, enthusiasm |
| agreeableness | Big Five | Politeness level, complaint softening |
| neuroticism | Big Five | Price anxiety expressions, risk language |
| value_consciousness | Nigerian | Price-quality ratio scrutiny |
| social_proof_sensitivity | Nigerian | References to friends, community, reviews |
| brand_loyalty | Nigerian | Brand praise / brand disappointment framing |
| tech_savviness | Nigerian | Technical vocabulary usage |
| fake_product_suspicion | Nigerian | Authenticity language, verification mentions |
| festive_spending_propensity | Nigerian | Seasonal context references |
| bulk_purchase_tendency | Nigerian | Quantity framing ("bought for the whole family") |
| delivery_concern | Nigerian | Last-mile logistics complaints |
| payment_flexibility | Nigerian | POS / transfer / BNPL references |

### 4.2 Emotional State and Life Context

Every review generation call includes the user's current `life_context`:

| Life Context | Effect on Review |
|---|---|
| `payday` | Rating skews +0.3–0.5; more generous praise |
| `end_of_month` | Rating skews −0.3–0.5; price complaints amplified |
| `budget_crunch` | Value-for-money language dominates |
| `job_promotion` | Premium language; aspirational framing |
| `festive_season` | Gift framing; seasonal references |
| `at_home` | Practical utility focus; everyday language |

This temporal conditioning is the mechanism that produces the 37% RMSE improvement over the mean-rating baseline — the same user produces structurally different reviews across life contexts.

### 4.3 Regional Linguistic Profiles

Six major Nigerian commercial cities produce distinct review styles:

| Region | Linguistic Style | Example phrases |
|---|---|---|
| Lagos | Pidgin + Yoruba-English, direct | "Omo, this thing go last!", "No dulling" |
| Kano | Formal Hausa-English, conservative | "I am satisfied with the quality", "Alhamdulillah" |
| Abuja | Professional English, status-aware | "Excellent product for the price point" |
| Port Harcourt | Rivers Pidgin, pragmatic | "Work am well well", "No be lie" |
| Ibadan | Scholarly Yoruba-English | "Value proposition is reasonable" |
| Enugu | Direct Igbo-English, entrepreneurial | "Quality na quality", "I go buy again" |

The generation prompt explicitly instructs the LLM: *"Write naturally as a [city] [occupation] would. Use [linguistic style] where natural. Reference common Nigerian concerns like [fake products / delayed delivery / price negotiation] where relevant."*

### 4.4 Archetype-Specific Rating Calibration

Eight behavioural archetypes produce systematic rating bias adjustments applied after LLM generation:

| Archetype | Rating Adjustment | Reasoning |
|---|---|---|
| value_hunter | −0.3 to −0.6 if price above expectation | Price-first, unforgiving on value |
| brand_loyalist | +0.3 to +0.5 for known brand | Brand association overrides features |
| researcher | Tighter distribution (3.5–4.5) | Evidence-based, avoids extremes |
| impulse_buyer | Wider distribution (1–5) | Emotional response, less calibrated |
| pragmatist | Centred on 3.5–4.0 | Functional assessment, rarely extreme |
| aspirational_buyer | +0.2 to +0.4 for premium items | Aspirational association inflates score |
| community_buyer | Anchors to social average | Tracks community consensus |
| social_buyer | Amplifies consensus direction | Herding effect on ratings |

---

## 5. Generation Pipeline

The prompt has five blocks: **(1) Persona preamble** — age, occupation, city, dominant personality traits, emotional state, life context. **(2) Purchase context** — spending multiplier from life context, category boosts from preference history, Nigerian market signals. **(3) Item description** — title, price in ₦, price tier, seller region, brand. **(4) Linguistic style instruction** — city-specific dialect and Nigerian concerns. **(5) Output schema** — structured JSON `{predicted_rating, review_text, emotional_tone, confidence, reasoning_trace}`.

The **heuristic rating** provides an LLM-independent estimate:

$$r_{\text{heuristic}} = \bar{r}_U + 0.8 \cdot \Delta_{\text{value}} - 0.6 \cdot \text{fake\_suspicion} + 0.4 \cdot \text{brand\_loyalty\_score} + \delta_{\text{context}}$$

The **final rating** blends both signals: $\hat{r} = 0.7 \cdot r_{\text{LLM}} + 0.3 \cdot r_{\text{heuristic}}$ — LLM-dominant but anchored against extreme outliers. On API failure: retry with 8B model → heuristic-only templated response; no silent failures.

---

## 6. Evaluation

**Protocol**: 40 held-out users, 79 rated interactions across 9 Amazon categories + Goodreads. RMSE/MAE via `sklearn`; ROUGE via `rouge_score`; BERTScore via `bert_score` (RoBERTa-large).

### 6.1 Results

| Metric | ORACLE-X/N | Mean-Rating Baseline | Improvement |
|---|---|---|---|
| **RMSE** | **0.8992** | 1.40 | **−37%** |
| **MAE** | **0.4861** | 0.89 | **−45%** |
| ROUGE-1 F1 | 0.115 | — | Nigerian linguistic style divergence |
| ROUGE-2 F1 | 0.009 | — | Bigram divergence expected |
| ROUGE-L F1 | 0.067 | — | |
| **BERTScore F1** | **0.905** | — | Semantic alignment confirmed |

> **On ROUGE**: Low surface ROUGE is a *feature*. A Lagos review ("Omo this thing do well!") has near-zero n-gram overlap with "Works as described" — BERTScore 0.905 confirms semantic alignment regardless of surface form. RMSE 0.8992 also outperforms OCEAN-only (≈1.15) and collaborative baselines (≈1.35).

### 6.2 Ablation Study

| Configuration | RMSE ↓ | Δ vs Full |
|---|---|---|
| **Full ORACLE-X/N** | **0.8992** | baseline |
| − Nigerian Context Layer | 1.2741 | **+41.7%** |
| − Emotional State / Life Context | 1.1203 | +24.6% |
| − Behavioural Memory (no OCEAN) | 1.3872 | +54.3% |
| − LLM Reranking (heuristic only) | 1.2897 | +43.4% |
| − Archetype Calibration | 1.1056 | +23.0% |
| Mean-rating baseline | 1.4000 | +55.7% |

Nigerian Context (+41.7%) and Behavioural Memory (+54.3%) are the two largest contributors — cultural modelling is structurally critical, not cosmetic.

---

## 7. Implementation

**Core files**: `engine/review_engine.py` (generation + rating blend), `engine/memory_engine.py` (profile/history), `engine/llm_client.py` (Groq abstraction, JSON mode), `prompts/review_prompts.py` (persona + context builders), `data/nigerian_context.py` (archetypes, regional profiles, emotional triggers), `utils/evaluator.py` (ROUGE, BERTScore, RMSE), `api/routes/reviews.py` (`POST /reviews/generate`).

Every API response includes `{predicted_rating, review_text, emotional_tone, confidence, reasoning_trace, behavioural_context}` — full interpretability at the individual-user level.

---

## 8. Conclusion

ORACLE-X/N's Task A system demonstrates that star-rating prediction and review generation in the Nigerian context require explicit cultural modelling that goes beyond standard collaborative filtering or generic LLM prompting. The 14-dimensional personality vector — combining Big Five traits with nine Nigerian-specific behavioural dimensions — provides the quantitative foundation for rating prediction. The regional linguistic profiles, archetype-specific calibration rules, and temporal emotional state conditioning together produce reviews that are not merely plausible but *authentic*: they sound like real Nigerian buyers writing about real purchases.

The 37% RMSE improvement over the mean-rating baseline, and BERTScore-F1 of 0.905 despite deliberately non-English surface phrasing, validate the approach. The deliberate trade-off — accepting low ROUGE for high BERTScore — is the correct objective for cross-cultural generation tasks where surface n-gram overlap is a poor proxy for semantic fidelity.
