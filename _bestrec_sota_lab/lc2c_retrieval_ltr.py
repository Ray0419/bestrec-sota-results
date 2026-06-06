"""Retrieval-first LC2C successor with validation-gated learned fusion.

The model is deliberately conservative:
- learn only on inner validation folds inside the development/confirmatory
  runner;
- combine existing full-catalog scorers as features;
- fall back to content-direct whenever validation does not show an improvement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor


ScoreFn = Callable[[np.ndarray], np.ndarray]


@dataclass(frozen=True)
class LTRConfig:
    method: str = "lc2c_retrieval_ltr"
    feature_methods: tuple[str, ...] = (
        "content_direct",
        "blair_text",
        "faithful_dropoutnet",
        "lc2c_v2",
        "lc2cpp_validated_margin",
        "melt_tail_transfer",
        "popularity",
    )
    negative_samples_per_positive: int = 32
    max_train_examples: int = 60000
    n_estimators: int = 120
    learning_rate: float = 0.04
    max_depth: int = 3
    min_validation_gain: float = 0.0
    score_batch_items: int = 2048
    rerank_top_m: int = 512
    rerank_anchor_method: str = "content_direct"
    rerank_anchor_methods: tuple[str, ...] = ()
    rank_feature_scope: str = "full"
    mask_seen_in_topm: bool = False
    validation_baseline_method: str = "content_direct"
    fallback_method: str = "content_direct"
    rerank_output_mode: str = "lift"
    rerank_prediction_weight: float = 1.0

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["feature_methods"] = list(self.feature_methods)
        payload["rerank_anchor_methods"] = list(self.rerank_anchor_methods)
        return payload


class RetrievalLTR:
    def __init__(self, config: LTRConfig, model: GradientBoostingRegressor | None, metadata: dict):
        self.config = config
        self.model = model
        self.metadata = metadata

    @property
    def used_fallback(self) -> bool:
        return self.model is None or bool(self.metadata.get("fallback_to_content"))

    def make_score_fn(
        self,
        base_scorers: dict[str, ScoreFn],
        content_scorer: ScoreFn,
        n_items: int,
        user_profile_norm: np.ndarray | None = None,
        seen_items_by_user: dict[int, set[int]] | None = None,
    ) -> ScoreFn:
        if self.used_fallback:
            return base_scorers.get(self.config.fallback_method, content_scorer)

        methods = [m for m in self.config.feature_methods if m in base_scorers]
        model = self.model
        if model is None or not methods:
            return content_scorer

        def score(user_ids: np.ndarray) -> np.ndarray:
            base_scores = {m: base_scorers[m](user_ids).astype(np.float32) for m in methods}
            anchors = _anchor_methods(self.config, base_scores)
            if self.config.rerank_top_m and anchors:
                rank_scores = None
                if self.config.rank_feature_scope == "full":
                    rank_scores = {m: _rank_percentiles(s) for m, s in base_scores.items()}
                return _score_topm_rerank(
                    model=model,
                    base_scores=base_scores,
                    rank_scores=rank_scores,
                    methods=methods,
                    user_ids=user_ids,
                    user_profile_norm=user_profile_norm,
                    seen_items_by_user=seen_items_by_user if self.config.mask_seen_in_topm else None,
                    anchor_methods=anchors,
                    top_m=min(self.config.rerank_top_m, n_items),
                    rank_feature_scope=self.config.rank_feature_scope,
                    output_mode=self.config.rerank_output_mode,
                    prediction_weight=self.config.rerank_prediction_weight,
                )
            rank_scores = {m: _rank_percentiles(s) for m, s in base_scores.items()}
            out = np.empty((len(user_ids), n_items), dtype=np.float32)
            profile = None
            if user_profile_norm is not None:
                profile = user_profile_norm[user_ids].astype(np.float32)
            for start in range(0, n_items, self.config.score_batch_items):
                end = min(n_items, start + self.config.score_batch_items)
                feats = _feature_block(base_scores, rank_scores, methods, start, end, profile)
                pred = model.predict(feats).astype(np.float32)
                out[:, start:end] = pred.reshape(len(user_ids), end - start)
            return out

        return score


def fit_retrieval_ltr(
    base_scorers: dict[str, ScoreFn],
    content_scorer: ScoreFn,
    train_inters: list[dict],
    validation_inters: list[dict],
    n_items: int,
    seed: int,
    config: LTRConfig,
    eval_full_catalog: Callable,
    dataset: str,
    fold_id: int,
    user_profile_norm: np.ndarray | None = None,
) -> RetrievalLTR:
    methods = [m for m in config.feature_methods if m in base_scorers]
    if not methods:
        return RetrievalLTR(config, None, {"fallback_to_content": True, "reason": "no_feature_methods"})

    X, y = _build_training_matrix(
        base_scorers=base_scorers,
        train_inters=train_inters,
        validation_inters=validation_inters,
        n_items=n_items,
        seed=seed,
        methods=methods,
        negative_samples=config.negative_samples_per_positive,
        max_examples=config.max_train_examples,
        user_profile_norm=user_profile_norm,
        rank_feature_scope=config.rank_feature_scope,
    )
    if len(y) < 100 or len(np.unique(y)) < 2:
        return RetrievalLTR(config, None, {"fallback_to_content": True, "reason": "insufficient_training_examples", "n_examples": int(len(y))})

    model = GradientBoostingRegressor(
        n_estimators=config.n_estimators,
        learning_rate=config.learning_rate,
        max_depth=config.max_depth,
        random_state=seed,
    )
    model.fit(X, y)
    candidate = RetrievalLTR(config, model, {"feature_methods": methods, "n_examples": int(len(y))})
    ltr_score = candidate.make_score_fn(
        base_scorers,
        content_scorer,
        n_items,
        user_profile_norm,
        seen_items_by_user=make_seen_items_by_user(train_inters),
    )
    ltr_val, _ = eval_full_catalog(dataset, seed, fold_id, config.method, ltr_score, train_inters, validation_inters, n_items)
    validation_baseline = base_scorers.get(config.validation_baseline_method, content_scorer)
    baseline_val, _ = eval_full_catalog(
        dataset,
        seed,
        fold_id,
        f"{config.validation_baseline_method}_validation",
        validation_baseline,
        train_inters,
        validation_inters,
        n_items,
    )
    gain = float(ltr_val["NDCG@10"] - baseline_val["NDCG@10"])
    metadata = {
        **candidate.metadata,
        "validation_ltr_ndcg10": ltr_val["NDCG@10"],
        "validation_baseline_method": config.validation_baseline_method,
        "validation_baseline_ndcg10": baseline_val["NDCG@10"],
        "validation_gain": gain,
    }
    if gain <= config.min_validation_gain:
        metadata["fallback_to_content"] = True
        metadata["fallback_method"] = config.fallback_method
        metadata["reason"] = "validation_safety_rule"
        return RetrievalLTR(config, None, metadata)
    metadata["fallback_to_content"] = False
    return RetrievalLTR(config, model, metadata)


def _build_training_matrix(
    base_scorers: dict[str, ScoreFn],
    train_inters: list[dict],
    validation_inters: list[dict],
    n_items: int,
    seed: int,
    methods: list[str],
    negative_samples: int,
    max_examples: int,
    user_profile_norm: np.ndarray | None,
    rank_feature_scope: str,
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.RandomState(seed)
    train_by_user: dict[int, set[int]] = {}
    positives_by_user: dict[int, list[int]] = {}
    for row in train_inters:
        train_by_user.setdefault(int(row["user_id"]), set()).add(int(row["item_id"]))
    for row in validation_inters:
        u = int(row["user_id"])
        if u in train_by_user:
            positives_by_user.setdefault(u, []).append(int(row["item_id"]))

    users = sorted(positives_by_user)
    rng.shuffle(users)
    X_blocks: list[np.ndarray] = []
    y_blocks: list[np.ndarray] = []
    n_examples = 0
    all_items = np.arange(n_items, dtype=np.int32)
    for user in users:
        pos_items = positives_by_user[user]
        forbidden = set(train_by_user.get(user, set())) | set(pos_items)
        available = np.setdiff1d(all_items, np.fromiter(forbidden, dtype=np.int32), assume_unique=False)
        if len(available) == 0:
            continue
        items: list[int] = []
        labels: list[float] = []
        for pos in pos_items:
            items.append(int(pos))
            labels.append(1.0)
            k = min(negative_samples, len(available))
            negs = rng.choice(available, size=k, replace=False)
            items.extend(int(x) for x in negs)
            labels.extend([0.0] * k)
        feats = _features_for_user(
            base_scorers,
            methods,
            user,
            np.array(items, dtype=np.int32),
            user_profile_norm,
            rank_feature_scope,
        )
        X_blocks.append(feats)
        y_blocks.append(np.asarray(labels, dtype=np.float32))
        n_examples += len(labels)
        if n_examples >= max_examples:
            break

    if not X_blocks:
        return np.zeros((0, _feature_count(len(methods))), dtype=np.float32), np.zeros((0,), dtype=np.float32)
    X = np.vstack(X_blocks).astype(np.float32)
    y = np.concatenate(y_blocks).astype(np.float32)
    if len(y) > max_examples:
        idx = rng.choice(np.arange(len(y)), size=max_examples, replace=False)
        return X[idx], y[idx]
    return X, y


def _features_for_user(
    base_scorers: dict[str, ScoreFn],
    methods: list[str],
    user: int,
    item_ids: np.ndarray,
    user_profile_norm: np.ndarray | None,
    rank_feature_scope: str,
) -> np.ndarray:
    uid = np.array([user], dtype=np.int32)
    score_mats = {m: base_scorers[m](uid).astype(np.float32) for m in methods}
    rank_mats = {m: _rank_percentiles(s) for m, s in score_mats.items()} if rank_feature_scope == "full" else {}
    profile = None
    if user_profile_norm is not None:
        profile = np.array([user_profile_norm[user]], dtype=np.float32)
    feats = []
    for m in methods:
        scores = score_mats[m][0, item_ids]
        ranks = rank_mats[m][0, item_ids] if rank_feature_scope == "full" else _rank_percentiles_1d(scores)
        if rank_feature_scope == "zsigmoid":
            ranks = _zsigmoid_rank_feature(score_mats[m][0], item_ids)
        feats.append(scores)
        feats.append(_safe_z(scores))
        feats.append(ranks)
    if profile is not None:
        feats.append(np.full(len(item_ids), profile[0], dtype=np.float32))
    else:
        feats.append(np.zeros(len(item_ids), dtype=np.float32))
    return np.vstack(feats).T.astype(np.float32)


def _feature_block(
    base_scores: dict[str, np.ndarray],
    rank_scores: dict[str, np.ndarray],
    methods: list[str],
    start: int,
    end: int,
    user_profile: np.ndarray | None,
) -> np.ndarray:
    feats = []
    for m in methods:
        block = base_scores[m][:, start:end]
        feats.append(block.reshape(-1))
        feats.append(_safe_z_rows(block).reshape(-1))
        feats.append(rank_scores[m][:, start:end].reshape(-1))
    n = base_scores[methods[0]].shape[0] * (end - start)
    if user_profile is None:
        feats.append(np.zeros(n, dtype=np.float32))
    else:
        feats.append(np.repeat(user_profile, end - start).astype(np.float32))
    return np.vstack(feats).T.astype(np.float32)


def _score_topm_rerank(
    model: GradientBoostingRegressor,
    base_scores: dict[str, np.ndarray],
    rank_scores: dict[str, np.ndarray] | None,
    methods: list[str],
    user_ids: np.ndarray,
    user_profile_norm: np.ndarray | None,
    seen_items_by_user: dict[int, set[int]] | None,
    anchor_methods: list[str],
    top_m: int,
    rank_feature_scope: str,
    output_mode: str,
    prediction_weight: float,
) -> np.ndarray:
    primary_anchor = anchor_methods[0]
    anchor = base_scores[primary_anchor]
    if output_mode == "rank_blend":
        out = _rank_percentiles(anchor)
    else:
        out = anchor.copy()
    weight = float(np.clip(prediction_weight, 0.0, 1.0))
    for row_idx, user_id in enumerate(user_ids):
        row = anchor[row_idx]
        if top_m >= row.shape[0]:
            item_idx = np.arange(row.shape[0], dtype=np.int32)
        else:
            item_parts = []
            seen = seen_items_by_user.get(int(user_id)) if seen_items_by_user is not None else None
            for anchor_method in anchor_methods:
                src = base_scores[anchor_method][row_idx]
                top_source = src
                if seen:
                    top_source = src.copy()
                    top_source[list(seen)] = -np.inf
                item_parts.append(np.argpartition(top_source, -top_m)[-top_m:].astype(np.int32))
            item_idx = np.unique(np.concatenate(item_parts)).astype(np.int32)
        profile = None
        if user_profile_norm is not None:
            profile = np.array([user_profile_norm[int(user_id)]], dtype=np.float32)
        feats = []
        for m in methods:
            vals = base_scores[m][row_idx, item_idx]
            ranks = _rank_feature_for_items(base_scores[m][row_idx], item_idx, rank_feature_scope, rank_scores[m][row_idx] if rank_scores is not None else None)
            feats.append(vals)
            feats.append(_safe_z(vals))
            feats.append(ranks)
        if profile is None:
            feats.append(np.zeros(len(item_idx), dtype=np.float32))
        else:
            feats.append(np.full(len(item_idx), profile[0], dtype=np.float32))
        pred = model.predict(np.vstack(feats).T.astype(np.float32)).astype(np.float32)
        # Keep the retrieval stage honest: only top-M anchor candidates are
        # reranked, and all non-top-M candidates retain their anchor score.
        full_anchor_rank = out[row_idx] if output_mode == "rank_blend" else None
        anchor_rank = _rank_feature_for_items(
            anchor[row_idx],
            item_idx,
            "full" if output_mode == "rank_blend" else rank_feature_scope,
            full_anchor_rank if output_mode == "rank_blend" else (rank_scores[primary_anchor][row_idx] if rank_scores is not None else None),
        )
        if output_mode == "rank_blend":
            pred_rank = _rank_percentiles_1d(pred)
            out[row_idx, item_idx] = (1.0 - weight) * anchor_rank + weight * pred_rank
        elif output_mode == "residual":
            out[row_idx, item_idx] = row[item_idx] + weight * _safe_z(pred) + 1e-4 * anchor_rank
        else:
            out[row_idx, item_idx] = float(np.nanmax(row)) + pred + 1e-4 * anchor_rank
    return out


def _rank_percentiles(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(scores, axis=1)
    ranks = np.empty_like(order, dtype=np.float32)
    rows = np.arange(scores.shape[0])[:, None]
    ranks[rows, order] = np.arange(scores.shape[1], dtype=np.float32)[None, :]
    denom = max(1, scores.shape[1] - 1)
    return ranks / denom


def _rank_percentiles_1d(scores: np.ndarray) -> np.ndarray:
    order = np.argsort(scores)
    ranks = np.empty_like(order, dtype=np.float32)
    ranks[order] = np.arange(len(scores), dtype=np.float32)
    return ranks / max(1, len(scores) - 1)


def _rank_feature_for_items(
    full_row: np.ndarray,
    item_idx: np.ndarray,
    scope: str,
    full_rank_row: np.ndarray | None,
) -> np.ndarray:
    if scope == "full" and full_rank_row is not None:
        return full_rank_row[item_idx]
    if scope == "zsigmoid":
        return _zsigmoid_rank_feature(full_row, item_idx)
    return _rank_percentiles_1d(full_row[item_idx])


def _zsigmoid_rank_feature(full_row: np.ndarray, item_idx: np.ndarray) -> np.ndarray:
    vals = full_row[item_idx].astype(np.float32)
    z = (vals - float(np.mean(full_row))) / max(float(np.std(full_row)), 1e-6)
    return (1.0 / (1.0 + np.exp(-z))).astype(np.float32)


def _safe_z(x: np.ndarray) -> np.ndarray:
    return ((x - np.mean(x)) / max(float(np.std(x)), 1e-6)).astype(np.float32)


def _safe_z_rows(x: np.ndarray) -> np.ndarray:
    return ((x - x.mean(axis=1, keepdims=True)) / np.maximum(x.std(axis=1, keepdims=True), 1e-6)).astype(np.float32)


def _feature_count(n_methods: int) -> int:
    return 3 * n_methods + 1


def _anchor_methods(config: LTRConfig, base_scorers: dict[str, ScoreFn]) -> list[str]:
    raw = [config.rerank_anchor_method, *config.rerank_anchor_methods]
    out: list[str] = []
    for method in raw:
        if method and method in base_scorers and method not in out:
            out.append(method)
    return out


def make_seen_items_by_user(interactions: list[dict]) -> dict[int, set[int]]:
    seen: dict[int, set[int]] = {}
    for row in interactions:
        seen.setdefault(int(row["user_id"]), set()).add(int(row["item_id"]))
    return seen
