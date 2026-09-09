# Novelty & feasibility audit — cold-start idea inventory
### 2026-08-06 · audit of every idea generated in this session, with verification status
### Honest accounting: several ideas were never novelty-checked, and one headline claim is now known to be substantially pre-empted.

---

## 0. Summary

**12 distinct ideas.** Novelty was verified thoroughly for the **4 I started with** (searched before proposing). It was **not** verified for the **8 that emerged from experiments** — which is backwards, because those 8 are what survived and became the contribution. Closing that gap today found:

- **3 ideas substantially pre-empted** (one of them a claim I presented to you as a key mechanism),
- **5 still plausibly novel**,
- **4 killed or refuted** on our own evidence.

Feasibility, by contrast, is **empirically established, not estimated**: 50 GPU training runs plus analysis passes all executed on the local RTX 5060 Ti.

---

## 1. The inventory

| # | Idea | Novelty verified? | Verdict |
|---|---|---|---|
| 1 | Derived EB gate (CLOSE / covariate-powered EB) replacing learned popularity gates | ✅ searched before proposing | **REFUTED by our experiment** (≤+0.0001, noise) |
| 2 | Interventional item-degree knockdown (k-dial) with frozen eval | ✅ searched (binary hiding is standard; graded intervention unoccupied) | **PLAUSIBLY NOVEL**, confirmed 5 seeds |
| 3 | Heteroscedastic spectral denoising of embedding tables | ✅ searched (RMT applied to MRI/finance/transformers, not rec tables) | **NULL** — loses to identity |
| 4 | Two-view BBP detectability | ✅ searched | **KILLED** before running |
| 5 | Exchange rate: cold gain vs warm cost, break-even p\* | ❌ **not checked until today** | ⚠️ **PARTIALLY PRE-EMPTED** — see §2.3 |
| 6 | **p\* ∝ √N_cold** scaling law | ❌ not checked | **PLAUSIBLY NOVEL**, but **experimentally unconfirmed** (3 points, 1 seed) |
| 7 | Directional collapse of cold rows ("suppression axis") as the unifying mechanism | ❌ **not checked until today** | ❌ **SUBSTANTIALLY PRE-EMPTED** — see §2.1 |
| 8 | Offset-matched efficiency ratio (diagnostic instrument) | ❌ not checked | **PLAUSIBLY NOVEL** (1.61 ± 0.07, 5 seeds) |
| 9 | Coarse-vs-fine: content improves within-pool AUC but not top-rank precision | ❌ not checked | **PLAUSIBLY NOVEL** as stated for cold-start content methods |
| 10 | Within-pool metric degeneracy on small cold pools | partially (via the parallel session's citations) | **PLAUSIBLY NOVEL** as a protocol correction |
| 11 | Text activation threshold at k ≈ 8–16 | ❌ not checked | **PLAUSIBLY NOVEL**, pre-registered and confirmed |
| 12 | Multi-dose simultaneous knockdown (experimental design) | ❌ not checked | **PLAUSIBLY NOVEL** as methodology; 6× cheaper and de-confounded |

---

## 2. The three pre-emption findings (checked 2026-08-06)

### 2.1 Directional collapse **is** representation degeneration — pre-empted

I reported the shared "suppression axis" (cold-row coherence +0.60 → +0.94) as the unifying mechanism explaining offset degeneracy. It is a **rediscovery of a known phenomenon**:

- **Representation Degeneration Problem** (Gao et al., ICLR 2019): token embeddings degenerate into an anisotropic narrow cone.
- **Rare Tokens Degenerate All Tokens** ([arXiv:2109.03127](https://arxiv.org/abs/2109.03127), ACL 2022): analyses training dynamics and shows *the gradient on rare-token embeddings is the cause* — rare tokens seldom receive positive gradients and are consistently pushed by negatives in a common direction, lowering effective rank. That is precisely our mechanism, including its dependence on never being a positive.
- In recsys specifically, **Rethinking Popularity Bias via Analytical Vector Decomposition** ([arXiv:2512.10688](https://arxiv.org/html/2512.10688v5)) reports that BPR "systematically organizes item embeddings along a dominant *popularity direction*" — our suppression axis.
- Embedding-norm/popularity coupling is likewise established: **Test-Time Embedding Normalization** ([arXiv:2308.11288](https://arxiv.org/pdf/2308.11288)); **Mitigating Popularity Bias: A Gradient Perspective** ([arXiv:2211.01154](https://arxiv.org/abs/2211.01154)).

**Consequence.** The mechanism cannot be claimed as a discovery. What may remain is the *bridge*: connecting representation degeneration to **offset degeneracy in cold-start evaluation** — i.e. that a shared direction cancels within-pool but not cross-pool, which is why a pool offset is such an efficient (and metric-gaming) repair. That bridge is an argument built on known parts, and must be presented that way, with these citations. Our sampled-negatives control (§5d) becomes a *replication* of the known gradient mechanism in a new architecture family, not a new mechanism.

### 2.2 Embedding-norm and popularity geometry — pre-empted
The norm gap (0.32 vs 0.55) and its reversal under sampled negatives are consistent with the popularity-magnitude literature above. Report as corroboration, not discovery.

### 2.3 The cold/warm exchange — partially pre-empted
The *tradeoff* is well known and even quantified in production work: **Warmer for Less** (Pinterest, WWW 2026, [arXiv:2512.17277](https://arxiv.org/html/2512.17277)) reports fresh-vs-aggregate outcomes; the coverage literature reports e.g. +10pp new-item coverage costing 4–5pp warm coverage. **Cold Item Integration via Tunable Stochastic Gates** ([arXiv:2112.07615](https://arxiv.org/abs/2112.07615)) already tunes cold promotion against conflicting warm objectives; **DiffCold** calls it the "seesaw dilemma".

**What may survive:** not the tradeoff, but (a) the **break-even prevalence** p\* = |c|/(g+|c|) as a decision rule, (b) its **√N_cold scaling**, and (c) the **offset-matched efficiency ratio** that separates genuine relevance from pool-shifting. These are sharper than "there is a tradeoff" — but (b) is experimentally unconfirmed and all three need a dedicated search before any claim.

---

## 3. What is still plausibly novel (best current estimate)

1. **The k-dial intervention + multi-dose design** (#2, #12) — graded, within-run, frozen-eval degree manipulation. Strongest methodological asset.
2. **The text activation threshold** (#11) — text contributes nothing below k ≈ 8–16, then switches on; 5 seeds, pre-registered.
3. **Offset-matched efficiency ratio** (#8) — an instrument that reads 1.0 for a disguised pool offset.
4. **Coarse-vs-fine resolution result** (#9) — content improves within-pool AUC (+0.02 to +0.12) while *failing* to improve top-rank precision.
5. **Within-pool metric degeneracy correction** (#10).

Note these are all **measurement/evaluation** contributions, not algorithmic ones. Every algorithmic idea in the inventory (#1, #3, #4) was refuted, null, or killed. That is a coherent identity for the work — and it matches this repository's existing strength — but it should be a deliberate choice, not a surprise.

---

## 4. Feasibility — verified by execution, not estimate

| item | evidence |
|---|---|
| k-dial machinery | 30 runs (5-seed replication) + 10 dose runs, all rc=0 |
| Multi-dose design | executed; 10 runs replace 60; groups balanced (2,800–3,700 targets each) |
| Decomposition harness | 11 decompositions across pool sizes 85 / 455 / 3,121 |
| Post-hoc posterior/imputation | executed on 5 checkpoints |
| Hardware headroom | RTX 5060 Ti 16 GB; MI run ≈ 4 min, VG ≈ 17 min; ~50 runs completed in one session |
| **Not** feasibility-tested | global-time protocol (new split pipeline), EB-NeRD, cross-dataset at scale (VG is 4× MI cost) |

---

## 5. Required next actions

1. **Dedicated novelty search for ideas #5, #6, #8, #9, #11, #12** — none has had one. Do this *before* any further GPU spend.
2. **Rewrite the mechanism sections** of `POC_RESULTS_COLDSTART.md` and `MERGED_COLDSTART_AGENDA.md` to cite representation degeneration and popularity-direction prior art, and to reframe our contribution as the *bridge* to offset degeneracy plus a replication under sampled negatives.
3. **Tell the parallel session**: their offset-degeneracy theorem is unaffected (it is about evaluation, not representation), but their write-up should cite the degeneration literature for *why* cold scores are jointly shifted.
