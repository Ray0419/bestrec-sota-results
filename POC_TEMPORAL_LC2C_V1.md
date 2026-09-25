# Temporal-LC2C V1 proof-of-concept design

Status: exploratory feasibility study; not preregistered, confirmatory, independent,
or paper-bound.

## Question

Does a validation-selected shared causal finite-impulse-response (FIR) recency
kernel improve LC2C's ranking of newly arriving items beyond a same-window
boxcar history?

## Data and split

- Dataset: timestamped Amazon Reviews 2023 `All_Beauty` 5-core LLOO CSVs.
- Catalog: 356 items with the existing 384-dimensional cached title embeddings.
- Inner development cutoff: pooled interaction-time quantile 0.60.
- Outer proof-of-concept cutoff: pooled interaction-time quantile 0.75.
- An item is cold at a cutoff when its first observed interaction is later than
  that cutoff. Its interactions are never used to fit EASE or LC2C at that stage.
- Candidate availability uses first observed interaction as a catalog-arrival
  proxy. This is imperfect and is a declared limitation.
- For every target, the user history contains only earlier warm-item interactions.

## Model and arms

EASE+content is fit on pre-cutoff warm interactions. LC2C uses ridge regression
from cached title embeddings to the fitted warm EASE coefficient columns.

The no-FIR control is an eight-position boxcar history. Candidate shared causal
FIR kernels are exponentially decaying eight-tap filters with decay in
`{0.50, 0.70, 0.85, 0.95}`. Every kernel is normalized to the same tap sum as
the boxcar. One kernel is selected on inner-development cold-pool NDCG@10 using
the average of the content-direct and LC2C arms, then frozen for the outer run.

The outer factorial arms are:

1. content-direct + boxcar;
2. content-direct + selected FIR;
3. LC2C + boxcar;
4. LC2C + selected FIR.

## Endpoints and falsification controls

Primary feasibility endpoint: paired per-user difference in cold-pool NDCG@10,
LC2C+FIR minus LC2C+boxcar. This endpoint is invariant to warm/cold score scale.

Secondary endpoint: the same contrast under full-catalog ranking after mapping
the cold score distribution to the warm EASE score distribution by per-event
mean/standard-deviation alignment (PZC). Raw uncalibrated full-catalog values
are also retained.

The factorial interaction is

`(LC2C_FIR - LC2C_boxcar) - (content_FIR - content_boxcar)`.

Bootstrap intervals resample users and are descriptive only: they do not cover
item, cutoff, dataset, or researcher-selection uncertainty.

## Feasibility interpretation

- Encouraging: LC2C+FIR improves both cold-pool and calibrated full-catalog
  ranking, with a positive interaction relative to content-direct.
- Weak/mixed: improvement appears only in one endpoint or is also present for
  content-direct, indicating a generic recency effect rather than LC2C synergy.
- Negative: LC2C+FIR does not improve cold-pool ranking. In that case adding FIR
  does not rescue LC2C's relevance ordering in this proof of concept.

No p-value or interval from this exploratory run may be called confirmatory.
