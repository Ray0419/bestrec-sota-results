#!/usr/bin/env python3
"""Prelaunch structural and conformance gates for PREREG_EE_V4."""

from __future__ import annotations

import ast

import torch

import ee_v4_common as common


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def test_training_sequestration() -> None:
    path = common.HERE / "run_ee_v4.py"
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    require("test_data.df" not in source, "training runner names TEST data")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = node.func.attr if isinstance(node.func, ast.Attribute) else (
            node.func.id if isinstance(node.func, ast.Name) else "")
        if name == "load_eval_inputs" and node.args:
            require(not (isinstance(node.args[0], ast.Constant)
                         and node.args[0].value == "test"),
                    "training runner loads TEST evaluation inputs")
        if name == "verify_data":
            for keyword in node.keywords:
                require(not (keyword.arg == "include_test"
                             and isinstance(keyword.value, ast.Constant)
                             and keyword.value.value is True),
                        "training runner verifies/reads TEST data")


def test_frozen_prior_and_upstream_default() -> None:
    common.verify_upstream()
    require(common.EEV3_ADJUDICATION.is_file(), "public E-E V3 adjudication missing")
    require(common.sha256(common.EEV3_ADJUDICATION)
            == common.EEV3_ADJUDICATION_SHA256,
            "public E-E V3 adjudication identity drift")
    upstream_cli = (common.UPSTREAM / "train.py").read_text(encoding="utf-8")
    upstream_model = (common.UPSTREAM / "models" / "backbone_SASRec.py").read_text(
        encoding="utf-8")
    require('ID_embs_init_type\', type=str, default="normal"' in upstream_cli,
            "upstream CLI normal-init default changed")
    require('nn.init.normal_(self.ID_embeddings.weight, 0, 1)' in upstream_model,
            "upstream normal-init implementation changed")
    for seed in common.SEEDS:
        words = common.key_words(common.ARMS[0], seed)
        require(words["ID_embs_init_type"] == "normal"
                and words["model_type"] == "SASRec"
                and words["random_seed"] == seed,
                f"frozen normal-init config drift: {seed}")


def test_model_contract() -> None:
    common.verify_data(include_test=False)
    frame = common.load_train_frame().iloc[:2]
    seq = torch.stack([torch.as_tensor(x, dtype=torch.long) for x in frame["seq"]])
    target = torch.as_tensor(frame["next"].to_numpy(copy=True), dtype=torch.long)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    seq = seq.to(device)
    target = target.to(device)
    seed = common.SEEDS[0]
    common.set_seed(seed)
    model = common.build_model(common.ARMS[0], seed, device)
    with torch.no_grad():
        state = model(seq)
        item = model.return_item_emb()
    require(state.shape == (2, 128), f"forward contract changed: {state.shape}")
    require(item.shape == (common.N_ITEMS + 1, 128),
            f"item-table contract changed: {item.shape}")
    weight = model.item_embeddings.ID_embeddings.weight.detach()
    require(bool(torch.isfinite(weight).all()) and float(weight.std()) > 0.9,
            "normal-init ID table is missing or degenerate")
    model.train()
    loss = model.calculate_infonce_loss(seq, target, 64, 0.07)
    require(bool(torch.isfinite(loss)), "InfoNCE smoke loss is non-finite")
    loss.backward()
    gradients = [p.grad for p in model.parameters() if p.grad is not None]
    require(gradients and all(bool(torch.isfinite(g).all()) for g in gradients),
            "smoke backward produced missing/non-finite gradients")
    require(any(bool(torch.count_nonzero(g)) for g in gradients),
            "smoke backward produced no active gradient")


def main() -> int:
    test_training_sequestration()
    test_frozen_prior_and_upstream_default()
    test_model_contract()
    print("PREREG_EE_V4 structural/conformance suite: PASS")
    print("TEST was not loaded; normal-init contract and frozen V3 identity verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
