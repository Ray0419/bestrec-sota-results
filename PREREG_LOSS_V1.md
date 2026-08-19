# PREREG: Is cold-item unrankability an artifact of the loss function? (V1)

**Frozen 2026-08-12 before any full gBCE run.** Smoke test (3 epochs) confirmed the implementation trains; no endpoint was inspected. Answers the threat-to-validity: *"your 'cold items score exactly zero' result may just be an artifact of chunked full cross-entropy."*

## 1. Arms

- **B0 (existing):** chunked full cross-entropy + label smoothing — already the strong choice per *Turning Dross Into Gold* (RecSys 2023), which showed full CE is what makes SASRec beat BERT4Rec.
- **L1 (new): gBCE**, the credible current SOTA loss — gSASRec, Petrov & Macdonald, RecSys 2023 / IJCAI 2024 ([arXiv:2308.07192](https://arxiv.org/abs/2308.07192)), **credited, reimplemented**: negative-sampling BCE with the positive term raised to power β, where α = K/(n_items−1) and β = α·(t(1−1/α) + 1/α). Config: t = 0.75, K = 256 (α = 0.0104, β = 0.2578).
- Everything else identical: same backbone, text channel, temporal protocol, seeds (20260736–38), 20 epochs.

## 2. Pre-registered prediction (recorded before the runs)

**P1 — cold NDCG@10 stays exactly 0.00000 under gBCE.** Structural reasoning: a cold item is *never a positive* under any loss in this family; full CE, sampled softmax, in-batch, BCE and gBCE all give never-target items downward gradient only. β recalibrates the positive/negative balance — it cannot make a never-positive into a positive. Prior evidence: the sampled-negatives control found directional collapse *strengthened* (coherence +0.60 → +0.94) under a different negative regime.

**P2 — warm NDCG@10 changes modestly (either direction).** gBCE's claim is matching full-CE quality with cheap sampling, and our baseline is already the strong full-CE variant.

**Falsification path I consider genuinely live:** gBCE exists to reduce overconfidence, which compresses the positive score range. If the warm-to-cold score gap narrows sufficiently, cold items could enter top-10 and **P1 fails** — which would mean unrankability is loss-dependent and the paper's §6.6 claim must be rescoped from "training cannot" to "full-CE training cannot."

## 3. Endpoints and decision rules

Primary: **cold NDCG@10** under the temporal protocol (3 seeds, MI).
- *P1 confirmed* iff cold NDCG@10 = 0.00000 in 3/3 seeds. The claim in §6.6 then strengthens to loss-family-invariant, stated across two distinct loss families and four training arms.
- *P1 refuted* iff any seed produces nonzero cold NDCG@10. Then §6.6 is **rescoped**, not deleted, and gBCE becomes a positive finding worth its own section — reported either way.

Secondary: warm NDCG@10, overall, within-pool AUC, and the full instrument battery (E1–E4) for like-for-like comparison against B0.

**Kill criteria.** No tuning of t or K after seeing cold results; if warm performance collapses (>50% below B0), the arm is declared a failed reimplementation and reported as such rather than used as evidence about cold items.

## 4. Cost

3 runs × ~2 min/epoch-equivalent ≈ 20 min GPU, plus 3 temporal evals.
