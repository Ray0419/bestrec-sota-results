# Related Work and Positioning (draft for the ρ(k)/π*(k,K) position paper)

**Drafted 2026-08-19 from DERIVATION_COVERAGE_BREAKEVEN.md, DESIGN_RHO_K_MATCHED_COVERAGE.md,
PREREG_RHO_K_V1.md §5, and the verified novelty boundaries of 2026-08-18. Organized by claim
boundary, not by topic: each cluster states what the prior work does and the exact residual we
claim on top of it.**

## A. Related work

### A.1 The coverage bottleneck and its failed mitigations

arXiv:2606.29947 measures the retrieval bottleneck in LLM-based cold-start recommendation across
five domains: a single retriever places the gold item in a 200-item pool only 4.6–22.9% of the
time, and 32–91% of cold-start targets are never covered. They then evaluate eight mitigations —
LLM scale (8B→70B), dense retrievers, two-tower models, reciprocal-rank fusion, CARA static
allocation, graph-evidence prompts, tail-prior injection, and LLM reranking — and report that
every one fails or is modest. All eight act on coverage; none acts on the conditional conversion
rate of a covered item. They also quantify the regime conflict of coverage-aware training as a
measured trade (5× upweighting of item-new positives: Yelp +10pp new-item coverage for −4.5pp
warm; Video Games +2.2pp for −4.7pp) and state it strictly as a measurement finding — no
break-even analysis, Pareto frontier, or constrained optimization is presented. Their conditional
metrics are stratified by coarse coldness buckets (item-new, item-cold, long-tail, user-cold,
warm), not by training degree. Our relationship to this paper is deliberately parasitic: we take
their measured coverage trade as cited constants, unmodified, and supply the decision formalism
they do not attempt — the break-even prevalence π\*(k,K) that says when, if ever, that trade pays.
Their eight negative results are then not eight independent facts but one fact: every mitigation
attacked Cov while R was the binding factor (§A.5 and the Discussion).

### A.2 Separating coverage from conversion

The decomposition of end-to-end success into coverage × conditional conversion is standard
two-stage retrieval analysis, and we claim no part of it. arXiv:2604.16318 already separates
reranking quality from retrieval coverage with a dual-regime protocol whose positive-controlled
regime guarantees the gold item is present in the pool; forcing coverage to 1 in order to read
conversion directly is their instrument, and injecting the gold item into a sampled candidate set
is older still — it is the sampled-metrics evaluation tradition, whose properties and pitfalls
are analyzed by Ekstrand et al. (arXiv:2309.11723). What these works do not produce is the object
we measure: the degree-resolved conversion curve R(k) under forced coverage, its warm-normalized
ratio ρ(k) = R(k)/R_warm, and the chain that carries ρ(k) into an allocation decision via
π\*(k,K) = c_cov/(g_cov·ρ(k) + c_cov). arXiv:2604.16318 uses the positive-controlled regime as a
benchmark condition; we use it as a measurement instrument and read a curve off it.

### A.3 Allocation of retrieval budget

Learned and operational allocation of candidate-generation budget exists and is not ours. CAPTS
(arXiv:2602.12564) coordinates trigger-to-channel assignment under per-channel retrieval budgets
with a learned value-attribution scorer and an explicit downstream-utility objective; it owns the
"downstream-utility-aware allocation" framing, provides no closed form, and its setting contains
no cold content (its users average roughly a thousand interactions). MIREC (arXiv:2305.12319)
allocates exposure shares across channels by an online-LP dual-price threshold — a data-driven
dual variable, not an analytic break-even. Multi-Decoder OneRec (arXiv:2607.26500) assigns
explicit per-route quotas to objective-specific retrieval routes; RealRoute (arXiv:2604.20860)
uses manually configured per-category caps with no cost-benefit derivation. These works allocate
along the channel or route axis, by learned or hand-set mechanisms; we derive a closed-form
break-even on the cold/warm axis, from cited constants plus one measured curve, and pair it with
an empirically measured drift budget (our out-of-sample audit found the break-even prevalence
drifts +19–31pp between adjacent time windows and is always optimistic, so the deployable rule is
prevalence > π\* + drift budget). The contribution is the arithmetic and its error bar, not an
allocation system.

### A.4 Production admission gates

Derived thresholds must be distinguished from tuned ones, and tuned ones are published. Google's
multi-funnel fresh-content system (KDD'23, arXiv:2306.01720) applies a graduation filter that
removes an item from the dedicated fresh funnel after ≥ n consumptions, with n set operationally;
Kuaishou's cold-start pipeline (WWW'25, 10.1145/3701716.3715205) gates items through
exposure-threshold growth phases. Admission rules for cold items therefore exist in production
practice. What does not exist, to our knowledge, is a rule whose threshold is derived from a
measurement: our k̂(K) is the smallest training degree at which π\*(k,K) falls below a plausible
deployment prevalence — an output of the ρ(k) instrument plus published constants, not a tuned
hyperparameter. The claim is "first measurement-derived", never "first".

### A.5 Cold-warm thresholds and the unrankability floor

arXiv:2508.07856 varies per-item training degree interventionally and measures the item cold-warm
transition at 6–15 interactions; it characterizes the threshold and proposes no rule for acting
on it. We cite it twice: as independent corroboration that the interesting structure in k is
below ~16, and as the foil that motivates a derived rule where the literature offers measured
transition points and ad hoc cutoffs. The floor that makes the rule bite — strictly cold items
are unrankable — is our program's most replicated finding (cold NDCG@10 exactly 0.00000 across
two loss families and five training arms) and is independently replicated in semantic-ID
generative retrieval by arXiv:2607.21101, which reports cold NDCG@20 = 0.00000 on
Beauty/Sports/Toys/WeiboTech. That is R_cold ≈ 0 in a third architecture family, measured by
authors with no stake in our thesis.

### A.6 Non-threats

Two adjacent works are structurally unrelated and are noted only to pre-empt the association.
arXiv:1601.04745 budgets exploration for a single cold target via a two-stage POMDP — a
per-target probe/batch schedule, not pool allocation and not prevalence-indexed. arXiv:2605.27439
audits LLM assistants nominating brands, stratified by prominence tiers; prominence there is an
externally sourced awareness footprint, not training interaction degree, its conversion rates run
25–52% (nowhere near ρ ≈ 0), and it derives no decision rule — we cite it only as independent
evidence that coverage and conversion dissociate by popularity tier.

## B. Claims and non-claims

**We claim three things.** (1) A closed-form break-even rule π\*(k,K) = c_cov/(g_cov·ρ(k) + c_cov)
on the cold/warm axis, deployed with an empirically measured drift budget (+19–31pp between
adjacent windows, always optimistic). (2) A degree-indexed admission rule k̂(K) — the smallest
degree at which buying a pool slot can pay — which is, to our knowledge, the first
measurement-derived admission threshold; tuned operational gates precede it (arXiv:2306.01720;
10.1145/3701716.3715205). (3) An explanation of arXiv:2606.29947's eight failed mitigations: all
eight attack coverage while conversion is the binding factor.

**We do not claim** the coverage × conversion decomposition (standard two-stage analysis;
arXiv:2604.16318), the gold-injection / forced-coverage protocol (sampled-metrics tradition;
arXiv:2309.11723; arXiv:2604.16318), the "downstream-utility-aware allocation" framing
(arXiv:2602.12564), or any algorithmic fix — this paper is a measurement and a decision rule, not
a method.
