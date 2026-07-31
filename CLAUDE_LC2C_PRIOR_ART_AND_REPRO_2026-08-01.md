# Claude memo — pre-FIR (BEST-Rec / LC2C) direction: reproduction PASSES, novelty does NOT

Role: scientific red-team + venue-methodology owner. Date: 2026-08-01. HEAD at start: `ae8f52db`.
Prompted by a maintainer question: *is the pre-FIR cold-item direction better than FIR?*
Advisory only — not peer review, not independent evidence.

```text
WORKSTREAM:        assess the pre-FIR BEST-Rec/LC2C direction as a publication candidate
OBJECTIVE:         (1) does it reproduce? (2) is it novel?
EVIDENCE QUESTION: would a reviewer accept LC2C as a contribution, and against which baselines?
FILES I MAY EDIT:  this memo; a Claude section in HANDOFF_CODEX.md
FILES I WILL NOT EDIT: PAPER_REVIEW_AUDIT.md, manuscript, TeX, cover letter, preregs,
                   adjudicators, graph, tables, manifest, results_*.json
EXPECTED OUTPUT:   reproduction verdict + prior-art verdict + what remains claimable
STOP CONDITION:    memo committed and pushed
```

## Part 1 — Reproduction: **PASS, bit-exact**

Re-ran `run_warm_loo.py beauty fashion` today against the committed 2026-05-22 artifacts.
Originals were backed up first and **restored afterwards** (`git checkout`), per the
never-overwrite-`results_*.json` rule; tree left clean.

| dataset/method | committed | re-run | delta |
|---|---:|---:|---:|
| beauty/popularity | 0.017670 | 0.017670 | 0 |
| beauty/ease_pure | 0.062835 | 0.062835 | 0 |
| beauty/higher_order_ease | 0.091970 | 0.091970 | 0 |
| beauty/ease_sbert | 0.092865 | 0.092865 | 0 |
| fashion/popularity | 0.037439 | 0.037439 | 0 |
| fashion/ease_pure | 0.075970 | 0.075970 | 0 |
| fashion/higher_order_ease | 0.091799 | 0.091799 | 0 |
| fashion/ease_sbert | 0.092258 | 0.092258 | 0 |

**Max absolute deviation 0.000e+00**, HR@10 and MRR also matched. Runtime **~1–2 minutes**,
CPU only. The merge behaved correctly (books/instruments preserved); the only file delta was
*added* provenance (`seed: 42`).

### Three findings the JSON did not show

1. **The warm evaluation is tiny.** The run log reports **beauty 253 users / 356 items / 2,535
   interactions** and **fashion 513 / 614 / 3,805**. That explains why `ease_sbert` vs
   `higher_order_ease` is `n.s.` on 3 of 4 datasets — there is almost no power to separate
   0.0929 from 0.0920.
2. **The deep baselines are not reproducible.** `run_warm_loo.py`'s own docstring states
   MultiVAE / iALS / LightGCN "remain in the legacy notebook"; `results_FINAL.json` marks them
   `legacy_prior_pipeline_preserved_by_consolidator`. So the comparison that makes the warm
   table look strong **cannot currently be re-derived**.
3. **No provenance chain.** All three result files were last touched at `251ef5a0`
   (2026-05-22) — the **first commit in the repository**. The results arrived as a snapshot;
   `_provenance` records only `generated_by` and `primary_inputs` — no data hashes, no code
   commit, no environment, no seeds. Re-running creates provenance going forward but cannot
   retroactively certify the May-22 numbers.

**Net:** the pipeline is faithful and cheap to verify. The *warm* claim is weak on power and
partly unverifiable. The *cold-item* claim (instruments n=3,911; books n=11,930) is the
substantive one and was **not** re-run this tick.

## Part 2 — Prior art: **the "new method" framing does not survive**

Method as implemented (`run_cold_item_v2.py:201–230`), stated exactly:

> **LC2C-V2** — fit EASE on warm items → item-item matrix `B_warm`; ridge-regress
> `SBERT_warm → B_warm.T` (each item's text embedding onto its **full item-item weight row**);
> predict that row for cold items; score `X[u, warm] @ B̂_cold`.

**LC2C-V1** (SBERT → SVD(`B`) latent k=64 → ridge) is the skeleton of **Gantner et al., ICDM
2010, *Learning Attribute-to-Feature Mappings for Cold-Start Recommendations*** — map item
attributes into the CF latent space and use predicted factors for cold items. Modern
embeddings, same move.

**LC2C-V2's premise is an established, named line.** Predicting the *linear-autoencoder*
item-item matrix from item content:

- **ELSA** (Vančura et al., 2022, *Scalable linear shallow autoencoder for collaborative
  filtering*) introduces factorizing the LAE item-item matrix as `B = A Aᵀ`.
- **beeFormer** (Vančura, Kordík & Straka, **RecSys 2024**, arXiv:2409.10309) trains
  sentence-Transformers so text embeddings reproduce interaction similarity in that framework,
  reporting gains specifically in **cold-start, zero-shot and time-split** settings — including
  on **Amazon Books**, which overlaps our Books dataset.
- **SEMCo** (**SIGIR 2026**, arXiv:2604.12990, DOI 10.1145/3805712.3809975) states verbatim, as
  *background*: *"following shallow LAEs (Vančura et al., 2022, 2024, 2025) in factorizing **B**
  so that **B = YYᵀ**, where **Y** … is a d-dimensional encoding of the item content features."*

Separately, **MARec** (arXiv:2404.13298) does cold-start with an **EASE** backbone and
closed-form solutions, evaluates on **Amazon Video Games**, and reports **+8.4% to +53.8%** over
prior SOTA — different mechanism (alignment regularisation), same problem, same backbone family,
overlapping domain.

### What is genuinely still distinctive

beeFormer **fine-tunes** the encoder by backpropagation. LC2C-V2 keeps SBERT **frozen** and fits
a **closed-form ridge** onto the full `B` row — seconds of CPU, no encoder training. The only
honest framing left is therefore a **strong-baseline / efficiency** claim, not a new method:

> *How much of the learned-encoder gain does a frozen-encoder closed-form ridge onto the LAE
> item-item matrix recover, at what fraction of the cost?*

That is a legitimate reproducibility/short-paper contribution — **conditional on benchmarking
against beeFormer, MARec and SEMCo**, which has not been done.

### The disqualifying gap as things stand

SEMCo's comparator set is **ALDI, CLCRec, GAR, GoRec, Heater**. Ours is DropoutNet, CLCRec,
`content_direct`, `cf_hybrid` — **one of five**. The headline **+119% on Books is measured
against `content_direct`**, not against any current cold-start method. That margin would not
survive contact with beeFormer.

## Part 3 — Verdict relative to FIR

Both directions have the same shape: a real but modest effect, in a crowded space, measured
against baselines that are not current. The cold-item direction has the **larger effect and
larger inferential units**; the FIR direction has the **provenance, preregistration and
adjudication discipline**. Neither has a defensible novelty claim as currently framed, and
neither has been compared to a current method.

**Recommendation:** stop hunting for a method contribution. The differentiated asset in this
repository is the **evaluation apparatus** — the artifact gate, frozen adjudicators, symmetric
self-VOIDing, and the retained record of retracted claims. Write that, using FIR *and* LC2C as
worked examples **including where both under-delivered**. That framing needs no new baselines to
be honest, and it is the one thing the competitor papers above do not have.

## Limits — important

I read abstracts, SEMCo's related-work passage (HTML), the beeFormer README, and search
summaries. **I did not read beeFormer's full method**: ACM returned HTTP 403 and the arXiv PDF
did not parse. I am therefore confident about *the line of work* and the `B = YYᵀ` framing —
because SEMCo states it verbatim with citations — but I am **not** asserting beeFormer's exact
internals, its baselines, or whether it already contains a frozen-embedding control. **Before
any decision rests on this, beeFormer and MARec must be read in full.** Prior-art searching is
also not exhaustive; absence of a hit is not evidence of novelty.

No sealed endpoint inspected, no protocol frozen, no manuscript/TeX/graph/table/manifest
modified, and every `results_*.json` restored to its committed state.
