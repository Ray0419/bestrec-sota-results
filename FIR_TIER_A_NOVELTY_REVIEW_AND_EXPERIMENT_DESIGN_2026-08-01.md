# FIR novelty review and confirmatory experiment design

Date: 2026-08-01  
Status: superseded by the later full-axis sweep in `CLAUDE_DECOMPOSITION_PRIOR_ART_SWEEP_2026-08-01.md`; no confirmatory campaign started  
Decision: **do not preregister the decomposition direction; submit the bounded FIR evaluation paper after release blockers are cleared**

## Executive decision

The current question - "does an identity-initialized causal FIR residual improve an HSTU-style sequential recommender?" - does **not** presently meet a defensible Tier-A method-novelty bar. The exact implementation may be previously unpublished, but the intellectual move is already crowded:

- FMLP-Rec showed that learnable filters can improve several existing sequential-recommendation backbones.
- C3SASR inserted causal convolutions into a self-attentive sequential recommender to capture local context.
- AdaMCT explicitly combined a CNN local filter with Transformer global attention.
- Recent methods add dynamic frequency selection, adaptive wavelets, user-adaptive filters, long causal convolutions, and position-varying causal filters.
- TV-Rec is the most direct collision: it formalizes a fixed causal convolution as a special case of a time/position-varying filter and reports a fixed-filter ablation on six datasets.

Changing the prose cannot manufacture method novelty. A credible Tier-A direction is instead a controlled empirical and mechanistic paper:

> **How much adaptive temporal structure is actually necessary in sequential recommendation? Under a fixed strong backbone, evaluator, initialization, optimization exposure, and candidate set, do ranking gains come from access to ordered causal lags itself, or from channel-specific, position-specific, user-adaptive, or spectral parameterization?**

This was initially assessed as conditionally promising, but the later full-axis sweep found position-specific, user-adaptive, spectral, and channel-specific axes already occupied, plus a public BSARec reproducibility preprint asking a closely related component-necessity question. The residual matched-harness gap is too narrow to justify delaying the current paper. The design below is retained as a historical specification, not a recommended campaign.

## Recommended paper identity

Working title:

> **What Do Adaptive Sequence Filters Actually Buy? A Controlled Study of Minimal Causal Mixing in Sequential Recommendation**

Alternative title:

> **How Much Temporal Mixing Do Sequential Recommenders Need?**

One-sentence contribution:

> We isolate temporal access from parameter count and nonlinear capacity, then measure when increasingly adaptive causal mixers yield practically meaningful gains under matched training, full-catalog evaluation, global-time validation, and cross-domain replication.

The FIR module is the lowest-complexity rung in an operator ladder. It is not presented as a new algorithm by itself.

## What the literature establishes

The review used primary paper pages and full-text PDFs available on 2026-08-01. "No paper found" below means no match in this scoped search; it is not proof of absence and should be checked by a domain expert before submission.

| Work | Closest relevant contribution | Consequence for this paper |
|---|---|---|
| Ferrari Dacrema et al., RecSys 2019 / TOIS 2021 | Reproducibility audit showing that many neural recommender gains disappear against reproducible, well-tuned simple baselines | Evaluation rigor and strong-simple-baseline auditing are important, but are not new contribution forms by themselves |
| Sequence or Pseudo-Sequence?, 2021 | Paired shuffled/unshuffled SASRec runs; reports that shuffling has little practical effect on several datasets | A generic "does order matter?" experiment is already prior art |
| Does It Look Sequential?, 2024; expanded journal analysis reported in 2026 | Uses sequence shuffling across many SR datasets; the expanded account distinguishes recency-based from order-sensitive patterns and assesses pattern complexity | Dataset-level order-necessity and order-versus-recency questions are already occupied |
| FMLP-Rec, WWW 2022 | Learnable frequency filters; also applies filters to several established SR backbones | "Adding a filter to another backbone" is not a sufficient contribution |
| C3SASR, 2022 | Causal convolutions before attention projections and after self-attention for local context | "Causal local convolution complements attention" is prior art |
| AdaMCT, CIKM 2023 | Adaptive mixture of CNN-based local filtering and Transformer global attention | Local/global hybridization is prior art |
| BSARec, AAAI 2024 | Fourier rescaling plus self-attention to separate low/high-frequency effects | Frequency-aware attention/filter combinations are crowded |
| SLIME4Rec, ICDE 2023 | Static and dynamic frequency selection across layers | A richer adaptive-filter story already exists |
| DWTRec, 2025 | Adaptive time-frequency filtering using wavelets | Time-frequency adaptivity is not an open method category |
| MUFFIN, CIKM 2025 | User-adaptive global and local frequency filters | Personalization of filters is prior art |
| TV-Rec, NeurIPS 2025 | Position-varying causal filtering; fixed filtering is a special case and an explicit ablation | This is the strongest collision with a fixed-FIR novelty claim |
| WEARec, AAAI 2026 | Adaptive frequency filtering plus wavelet enhancement | Current competitive filter baseline |
| HyenaRec, WWW 2026 | Gated, parameterized long causal depthwise convolutions; includes HSTU comparisons and kernel ablations | Current competitive causal-convolution baseline |
| Mamba4Rec, 2024 | Selective state-space sequence mixing for efficient SR | A modern non-attention temporal mixer is required in context |
| ConvRec, IJCAI-ECAI 2026 | Hierarchical strided convolution for efficient SR | Efficiency claims need direct modern comparison |

Primary pages:

- Are We Really Making Much Progress?: https://arxiv.org/abs/1907.06902
- A Troubling Analysis of Reproducibility and Progress: https://arxiv.org/abs/1911.07698
- Sequence or Pseudo-Sequence?: https://ceur-ws.org/Vol-2955/paper8.pdf
- Does It Look Sequential?: https://arxiv.org/abs/2408.12008
- FMLP-Rec: https://arxiv.org/abs/2202.13556
- C3SASR: https://arxiv.org/abs/2211.01297
- AdaMCT: https://arxiv.org/abs/2205.08776
- BSARec: https://arxiv.org/abs/2312.10325
- SLIME4Rec: https://arxiv.org/abs/2305.04322
- DWTRec: https://arxiv.org/abs/2503.23436
- MUFFIN: https://arxiv.org/abs/2508.13670
- TV-Rec: https://arxiv.org/abs/2510.25259
- WEARec: https://ojs.aaai.org/index.php/AAAI/article/view/38640
- HyenaRec: https://arxiv.org/abs/2603.25027
- Mamba4Rec: https://arxiv.org/abs/2403.03900
- ConvRec: https://arxiv.org/abs/2605.04723
- TASIF: https://arxiv.org/abs/2512.24246

## The plausible residual gap

The literature already compares whole models, tests sequence shuffling, distinguishes order from recency, and often includes architectural ablations. Therefore the broad questions "does order matter?" and "are complex neural recommenders really necessary?" are not available novelty claims. This review did not find a paper that jointly provides all of the following narrower design:

1. an exact same-backbone intervention that changes only access to ordered past source positions;
2. a nested ladder from current-position control to shared FIR, per-channel FIR, position-varying filtering, and user-adaptive filtering;
3. matched optimization exposure and validation-only tuning budgets;
4. full-catalog evaluation under a primary global-time protocol;
5. paired multi-seed inference across multiple independent domains; and
6. artifact-gated, fail-closed release and a separate replication custodian.

That conjunction is the potential novelty. In particular, M1 versus M2 is not a shuffled-data test: it preserves each example, target, item multiset, parameterization, arithmetic pattern, and optimizer exposure while changing only the source index available to the mixer. The proposed ladder then tests whether increasingly adaptive parameterizations add value after causal source access is established. It is a methodological and empirical gap, not a claim that FIR filters, order ablations, or recommender audits are new.

Because the residual distinction is narrow, a qualified external researcher should review the exact equations and nearest-paper matrix before any Tier-A novelty assertion. Search cannot certify absence.

## Audit of the current evidence

The current FIR evidence is useful for generating the revised hypothesis, but it is not a confirmatory basis for a Tier-A claim.

### Evidence that is genuinely encouraging

- On the current Movies & TV campaign, learned FIR versus identity is positive: approximately +0.002265 NDCG@10 with a reported paired interval [0.001928, 0.002602].
- Learned FIR separates from the current-position pointwise control: approximately +0.001941 [0.001788, 0.002095]. This suggests ordered source positions may matter.
- The artifact-gated workflow, sealed endpoint reading, and fail-closed evidence graph are stronger than typical informal experimental practice.

### Evidence that weakens the current method claim

- Learned depthwise FIR does not separate from the 16-parameter shared causal filter: approximately -0.000081 [-0.000337, 0.000175]. The existing result supports "small causal mixing may suffice" more than "the proposed learned per-channel FIR is needed."
- The positive discovery and follow-up evidence is concentrated in Amazon-style leave-one-out settings and is outcome-known. It is not an independent confirmation.
- MovieLens is undertrained in the current comparison: roughly 100 optimizer updates versus approximately 4,000-9,680 updates in Amazon campaigns. A null under this schedule is not valid evidence of a domain moderator.
- Post-hoc 400-484 update prefixes of a longer learning-rate schedule do not repair schedule mismatch; fresh full schedules are required.
- Existing comparator runs do not yet establish equal architecture, loss, update, token, validation-search, or candidate-set opportunity.
- Global or rolling time, another non-Amazon domain, fair modern baselines, and independent replication remain absent.

### Audit verdict

- Current algorithm novelty: **fail**.
- Current empirical observation: **real enough to motivate a stronger study, but outcome-known and narrow**.
- Current Tier-A readiness: **fail**.
- Revised controlled-minimality question: **conditionally plausible**, pending expert gap review and confirmatory results.

## Exact hypotheses

All thresholds and analysis code must be committed before confirmatory test endpoints are read.

### H1: ordered temporal access

An ordered-lag mixer outperforms a same-capacity current-source control when every operation except source index is held fixed.

Primary contrast: `M2 - M1 > 0` in full-catalog NDCG@10.

Interpretation: supports access to ordered history, not the necessity of FIR channel specificity.

### H2: minimal causal mixing

A 16-parameter shared causal FIR outperforms exact identity.

Primary contrast: `M3 - M0 > 0`.

Interpretation: supports usefulness of minimal causal mixing in the tested backbone and protocol.

### H3: adaptivity necessity

The shared FIR is non-inferior to more adaptive mixers within a predeclared practical margin.

Primary contrasts: `M3` versus `M4`, `M5`, and, if implemented, `M6`.

Provisional margin: 0.0005 absolute NDCG@10. This is only a starting value. It must be justified by practical utility and frozen before new confirmatory outcomes; it cannot be chosen because it makes the current result pass.

### H4: domain and protocol moderation

Any advantage is stable across independent domains, or is explained by a preregistered train-only moderator such as sequence length, lag predictability, popularity concentration, or temporal drift.

### H5: system-level relevance

The minimal mixer remains competitive after fair validation-only tuning against official modern systems, while providing a measurable efficiency advantage.

## Mechanism experiment: exact operator ladder

Use the same HSTU-style or SASRec block and replace only the temporal-mixing intervention.

| Arm | Definition | Purpose |
|---|---|---|
| M0 | Exact identity | No-mixer baseline |
| M1 | Current-source control with the same parameterization and arithmetic pattern as M2 | Isolates capacity/nonlinearity without access to past positions |
| M2 | Ordered-lag source mixer with the same parameters and operations as M1; only source indices differ | Clean test of temporal access |
| M3 | Canonical shared causal FIR with `K` learned taps shared across channels | Minimum LTI temporal mixer |
| M4 | Per-channel depthwise causal FIR with `K*d` taps | Tests channel-specific adaptivity |
| M5 | Position-varying TV-Rec-style causal filter adapted inside the same backbone | Tests position-specific adaptivity |
| M6 | User-adaptive filter, only if an equation-matched and auditable implementation is feasible | Tests personalization |

For the key M1/M2 control, use frozen signed-permutation channel transforms `P_l` so each lag coefficient remains identifiable in both arms:

`y_t = x_t + sum_l a_l P_l x_{s(t,l)}`

- M1 uses `s(t,l) = t` for every `l`.
- M2 uses `s(t,l) = t-l`, with causal padding.
- The number of learned scalars, transforms, additions, nonlinearities, initialization, and optimizer exposure are identical.
- The only intended difference is whether a coefficient can read an ordered past position.

M5 must be called a "TV-Rec-style adapted operator," not a reproduction of official TV-Rec. The official system belongs in the separate system benchmark.

## System benchmark

Run official or author-released implementations under a shared data/evaluation contract where licenses permit:

- SASRec or the selected strong backbone;
- official TV-Rec;
- official WEARec;
- official HyenaRec;
- optionally MUFFIN/BSARec if compute and preprocessing parity can be audited.

Do not claim architectural isolation from this benchmark. It asks whether the controlled finding matters against real systems. The mechanism experiment provides isolation.

## Datasets and split protocol

### Confirmatory domains

Use at least four substantially different domains:

1. MovieLens-1M;
2. Yelp;
3. Steam;
4. LastFM or another lawfully redistributable non-Amazon interaction dataset.

Retain one Amazon category only as an outcome-known robustness set. It cannot be the primary confirmation because current Amazon outcomes influenced the question and design.

Before touching confirmatory outcomes, freeze:

- source URL and license;
- raw-file cryptographic hash;
- all filtering thresholds;
- timestamp conversion and tie rules;
- user/item vocabulary policy;
- train/validation/test boundaries;
- catalog construction and cold-item treatment.

### Primary evaluation: global time

- Choose train, validation, and test cutoffs globally from timestamps.
- Build features and model-selection statistics from training-era data only.
- Define the candidate catalog at query time according to a frozen availability rule.
- Count an unavailable/unrepresented target as a miss and report target coverage; do not silently drop it.
- Prevent future user/item frequencies or sequence statistics from entering training features.

### Sensitivity evaluation

- Existing leave-last-one-out results are secondary sensitivity analyses.
- Add at least one rolling-origin global-time sensitivity if compute permits.
- Report how conclusions change with split style rather than pooling incompatible protocols.

## Backbones

The minimum credible design uses two backbones:

- the present HSTU-style all-position backbone; and
- SASRec as a widely understood self-attention backbone.

If only HSTU is used, the conclusion must be limited to that implementation family. A third mixer family such as Mamba4Rec would improve generality but materially increases engineering and tuning cost.

## Training and tuning parity

For every `(dataset, backbone, seed)` block:

- start all mechanism arms from the exact same backbone initialization;
- use identical batch construction, optimizer, learning-rate integral, valid-position count, loss, negative policy, and number of updates;
- interleave or randomize arm order to reduce time/hardware confounding;
- keep matched blocks on the same hardware type;
- record examples, non-padding target tokens, optimizer updates, and wall time;
- fail closed if any planned arm is missing or any endpoint was read before sealing.

Use development-only calibration to choose a common adequate budget. A reasonable planning range is 4,500-5,000 updates, but the actual budget must be selected from validation curves and then frozen.

MovieLens must be rerun from scratch at complete schedules such as 500, 2,000, and 5,000 updates if schedule sensitivity is studied. A checkpoint prefix from a longer cosine schedule is not equivalent to a separately scheduled shorter run.

For system baselines, grant the same number of validation-only trials, for example 12 configurations with one tuning seed, followed by a fixed eight-seed assessment. Record the full search space and every attempted configuration, including failures.

## Endpoints

Primary:

- full-catalog NDCG@10.

Secondary:

- HR@10 and MRR@10;
- NDCG/HR@20;
- target rank and top-10 list disagreement;
- candidate and target coverage;
- head/mid/tail item performance;
- performance by sequence length and temporal-drift strata;
- parameter count, FLOPs, peak accelerator memory, examples/s, and end-to-end latency on one fixed hardware/software stack.

Do not merge timing results from different GPUs or from the Apple laptop into one efficiency comparison.

## Statistical plan

- Use eight fixed assessment seeds per arm.
- Pair arm differences by seed within each dataset/backbone block.
- Report effect sizes and 95% confidence intervals, not only p-values.
- Apply Holm correction across the declared primary superiority contrasts.
- Use a user bootstrap and an item bootstrap as sensitivity analyses; do not treat repeated users or seeds as independent datasets.
- Treat the dataset/domain as the unit of generalization.
- Report a random-effects cross-domain estimate with Hartung-Knapp uncertainty and a prediction interval. With four domains, explicitly acknowledge that heterogeneity estimation remains imprecise.
- Require non-inferiority to pass per dataset and in the cross-domain analysis; do not allow one large dataset to mask a material loss elsewhere.
- Publish all null and negative planned contrasts.

## Decision gates

### Gate 0: novelty review

Before coding the full campaign, obtain written review from at least one sequential-recommendation researcher who was not involved in the current experiments. Ask specifically whether TV-Rec, C3SASR, AdaMCT, HyenaRec, MUFFIN, WEARec, or another paper already answers the exact minimality question.

Proceed only if the contribution is framed as controlled minimality/evaluation and the source-index control is judged meaningfully distinct.

### Gate 1: validation-only engineering pilot

Run M0-M3 on two development datasets with three seeds. Do not inspect or report confirmatory TEST outcomes. The pilot is for:

- checking equality of parameter/operation contracts;
- verifying adequate convergence;
- estimating runtime and variance;
- validating the sealed adjudication pipeline.

Proceed only if the code and exposure checks pass. Do not require a positive efficacy result from a pilot used to debug the protocol.

### Gate 2: mechanism confirmation

Run the frozen operator ladder. Stop FIR method framing if M2 does not beat M1. Stop the minimality claim if adaptive arms materially outperform M3 on most independent domains.

### Gate 3: system relevance

Proceed to a Tier-A submission only if the controlled result survives fair comparisons to current systems and either:

- the minimal shared FIR is non-inferior across domains while being materially simpler/faster; or
- a preregistered, replicated moderator accurately identifies when extra adaptivity is necessary.

### Gate 4: independent replication

A different investigator must receive the frozen protocol and untouched endpoints, reproduce at least two domains, and own the first-read adjudication. This may be called independent only if the investigator did not design/tune the original campaign and the custody separation is documented.

## Publication interpretation matrix

| Result | Defensible paper |
|---|---|
| M2 beats M1; M3 is non-inferior to adaptive filters across domains | Strong minimality/simplicity paper |
| Adaptive methods win, with a replicated train-only moderator | Strong conditional-adaptivity paper |
| Effects occur only on Amazon leave-one-out | Narrow benchmark observation; not Tier-A method evidence |
| M2 does not beat M1 | Temporal-access mechanism unsupported; stop FIR framing |
| Results depend on undertraining or unequal tuning | Invalid comparison; repair protocol before interpretation |
| Clean multi-domain null with strong equivalence bounds | Potential rigorous negative-results/evaluation paper, venue dependent |

## Scale, time, and resources

An illustrative full mechanism study with six arms, two backbones, four confirmatory datasets, and eight seeds is 384 assessment runs. A four-system benchmark over four datasets and eight seeds adds 128 assessment runs, before validation searches.

Planning estimate:

- validation-only kill pilot: 1-2 days and roughly 12-24 short runs;
- implementation, parity tests, and preregistration: 1-2 weeks;
- full campaigns: approximately 100-250 accelerator-hours, depending on dataset sizes and baseline efficiency;
- adjudication, robustness, and writing: 2-4 weeks;
- independent replication: an additional 1-3 weeks, often overlapping;
- storage: approximately 100-250 GB if checkpoints, ranks, logs, and environment artifacts are retained.

The expected end-to-end calendar is roughly 4-8 weeks with reliable accelerator access. These are planning estimates, not promises.

## Immediate implementation sequence

1. Freeze this revised research question and get the Gate 0 expert review.
2. Write `PREREG_TEMPORAL_MIXING_MINIMALITY_V1.md` with exact datasets, hashes, arms, budgets, seeds, endpoints, margins, and stop rules.
3. Implement M1/M2 first and prove parameter-count, operation-count, initialization, and gradient parity with unit tests.
4. Implement M0/M3/M4 and the adapted M5; keep official TV-Rec in a separate runner.
5. Build global-time dataset manifests without opening confirmatory outcomes.
6. Run the validation-only Gate 1 pilot.
7. Audit the pilot and freeze the final budget and tuning contract.
8. Commit the preregistration and adjudicator before starting confirmatory training.
9. Run all training and sealed evaluations; make the committed adjudicator the first endpoint reader.
10. Integrate the exact verdict, including failed gates, into the paper and artifact graph.

## Bottom line

The present FIR component is not sufficiently novel as a standalone Tier-A algorithm. The best defensible direction is to make the paper answer a harder and more general question: whether the field's increasingly adaptive temporal filters buy anything beyond clean access to ordered causal history under genuinely matched conditions. The existing shared-filter result makes this question scientifically interesting, but only new, frozen, multi-domain experiments can make it publishable.
