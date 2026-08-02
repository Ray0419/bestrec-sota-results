# Claude memo — candidate RQ #10: where does content stop helping?

**STATUS: EXPLORATORY, NOT PREREGISTERED. NOVELTY ~80–85%, BELOW THE 95% BAR.**
Date: 2026-08-01. Role: scientific red-team. Licenses no manuscript claim.

Emerged after nine directions were closed (see
[`CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md`](CLAUDE_RQ_FILTER_OVERPARAM_2026-08-01.md) §8–9).
**This is the first constructive candidate of the session and the first with a large effect.**

---

## 1. The received wisdom this would test

The field's stated position, recurring across the cold-start literature:

> *"Leveraging side content information does not significantly improve performance in the
> warm-start setting, but mostly allows to address the cold-start problem."*

I.e. content is for **cold** items (zero interactions). Once an item is warm, collaborative signal
suffices. This is treated as settled and is why nearly all content work targets the cold regime.

## 2. Our own data contradicts it — and found the boundary unprompted

The voided E-G campaign let validation freely choose a text weight **per popularity bin**. From
`_bestrec_run/eg_coldfuse_explore_verdict.json`, the selected configuration on **both** seeds:

| seed | `wt_tail` | `wt_mid` | `wt_head` | tail gain |
|---:|---:|---:|---:|---:|
| 20260721 | **0.2** | **0.0** | **0.0** | +0.00207 |
| 20260722 | **0.2** | **0.0** | **0.0** | +0.00222 |

Compare against the *global* (unbinned) text weight selected on the same seeds:

| variant | tail gain |
|---|---:|
| single global weight | +0.00050 |
| **per-bin weights** | **+0.00207 (4.1×)** |

**Nothing forced this.** The search could have chosen any weights; it independently drove mid and
head to **exactly zero** and concentrated all content weight on the tail. That is a step function
discovered by the data, and it is the crossover made visible.

Consistent with this, the campaign reported tail-bin NDCG@10 gains on **all five categories tested
(+0.0011 to +0.0048)** at aggregate cost within margin.

**Crucially, these items are not cold — they are sparse-warm** (non-zero but few interactions).
The received wisdom says content should not help them. It does.

## 3. The question

> **RQ.** As an item's interaction count grows, at what point does content stop contributing to
> ranking quality — and is that crossover a stable, predictable quantity across domains, or an
> artifact of each dataset?

Sub-questions:
- **RQ1 (existence).** Is the content-gain-vs-frequency curve monotone decreasing with a
  well-defined zero-crossing, rather than noise?
- **RQ2 (location).** Where is it, in interaction counts? Is it stable across categories, or does
  it scale with catalog size / density / sequence length?
- **RQ3 (prescription).** Does bin-targeted content allocation beat uniform allocation by the
  ~4× the E-G data suggests, on a clean prospective split?

## 4. Why this is a better shape than the nine that failed

| failure mode of directions 1–9 | this direction |
|---|---|
| **Deflationary** ("X is unnecessary") — failed because components *are* necessary | **Constructive** — measures a quantity and yields an allocation rule |
| Effects ~0.001–0.006 NDCG vs seed sd ~0.002 — underpowered | Tail-bin effects **+0.0011 to +0.0048**, and the *targeting* effect is **4×** |
| One dataset, one model | Already replicated across **5 categories** |
| Contradicted nothing — just proposed a saving | **Contradicts a stated belief** in the literature, which is what makes a finding publishable |
| Off-topic for the manuscript | Directly on the paper's own title: *Tackling Sparsity and Cold-Starts* |

## 5. Novelty — honest assessment, ~80–85%, NOT yet at the bar

**Searched and found unoccupied:**
- A **quantified crossover** — "how many interactions before content stops helping". Two separate
  searches returned no specific study; the second explicitly reported no empirical work giving
  such a transition point.
- Content helping the **sparse-warm** regime specifically. The literature distinguishes cold
  (zero) from long-tail (sparse non-zero) but concentrates almost entirely on cold: SEMCo (2026),
  sparse multimodal representations (2026), content-based initialisation (RecSys 2025),
  contrastive CF for cold items (WWW 2023).

**Known and occupied — the risk:**
- **Popularity-stratified evaluation is standard practice** (head/mid/tail bins are routine), so
  the *qualitative* claim "content helps the tail more" is almost certainly known, possibly folklore.
- Popularity-bias literature is large and adjacent.

**What must be checked before this can be called ≥95% novel:**
1. Forward citations of the cold-start surveys for any content-gain-vs-frequency curve.
2. Hybrid/switching recommender literature from the 2000s — bin-targeted content allocation may
   be old news under a different name (this is my main suspicion).
3. Whether any paper reports the *zero-crossing* rather than just head/tail buckets.

**I am not claiming this clears the bar.** It is the strongest remaining lead, not a confirmed one.

## 6. Cheapest decisive next step

Do **not** scale first. The E-G endpoints are exposed and cannot be reused, so:

1. **Novelty first** (hours, no compute) — the three checks in §5. If bin-targeted content
   allocation turns out to be classical hybrid-switching, this dies immediately and cheaply.
2. **Then a pilot** (small) — on one *fresh* category never used by E-G/E-G2, compute the
   content-gain-vs-frequency curve with per-bin weights and 5 seeds. Pre-declare that the curve
   must be monotone decreasing with a zero-crossing, and that mid/head optimal weights must be
   ≈0. If the step function does not reproduce, stop.
3. **Only then** the multi-category prospective study, with the margin set from a **power
   calculation** — the error I made in the filter work, where a 10%-of-effect margin turned out to
   need ~110 seeds.

## Limits

Exploratory. The E-G evidence is from an **exposed, protocol-deviated campaign** — it can motivate
a hypothesis and nothing more; it cannot support any claim. Two seeds for the per-bin selection.
Novelty is ~80–85%, below the bar, with a named path to close it and a specific suspicion
(classical hybrid switching) that could kill it outright. Nothing here licenses a manuscript claim.

---

## 7. RESULT: novelty check FAILED. Direction withdrawn. (2026-08-01, same day)

The §5 suspicion — "classical hybrid switching may already do bin-targeted content allocation" —
was correct. The check cost no compute and killed the direction, which is what it was for.

**The switching-hybrid literature occupies this completely:**

| prior work | what it already does |
|---|---|
| **Burke, hybrid recommender taxonomy (2002)** | *Switching* hybrids are a named class: use one recommender under stated conditions, switch when they fail |
| **DailyLearner** | Content-based first; falls back to collaborative when content confidence is insufficient |
| Published switching rules | *"switches to thematic filtering if a user has fewer than S=40 ratings (threshold chosen empirically)"*; *"fewer than five reliable neighbours"*; *"user_interaction_count < 5 → content-based"* |
| Adaptive-weight hybrids | *"hybridization weights adaptive based on the stage… initially depending more on non-personalized strategies and shifting weight to personalized approaches as it gains more user preference knowledge"* |

That last row **is** the crossover: a weight that moves from content to collaborative as
interactions accumulate. And the thresholds have been chosen empirically for two decades.

**So the E-G selection of `wt_tail=0.2, wt_mid=0.0, wt_head=0.0` is a rediscovery of a classical
switching hybrid, not a new quantity.** The 4.1× advantage of targeted over uniform allocation is
real and internally consistent, but it is the textbook justification for switching hybrids
existing at all — not evidence against received wisdom.

**Novelty: well below 95%. Direction withdrawn.** No compute was spent beyond two searches, which
is the whole value of running the cheap check before the pilot.

### Correction to §1 of this memo

I framed the field's position ("content helps cold, not warm") as a belief our data contradicts.
That framing was wrong in a way I should have caught: the switching literature's *entire premise*
is that the content→collaborative handover happens gradually across sparse-but-nonzero histories,
not at exactly zero interactions. Our data agrees with the literature; it does not contradict it.
I built the case for §2 before checking §5, and the ordering flattered the hypothesis.
