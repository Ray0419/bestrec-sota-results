#!/usr/bin/env python3
"""Structural/conformance tests for the frozen WEARec V1 adapter."""

from __future__ import annotations

import inspect
import math
import sys

import numpy as np
import torch

import wearec_baseline_v1_common as common


class DummyModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.item_embeddings = torch.nn.Embedding(4, 1)
        with torch.no_grad():
            self.item_embeddings.weight[:, 0] = torch.tensor([0.0, 1.0, 2.0, 3.0])

    def predict(self, input_ids, user_ids):
        return torch.ones((*input_ids.shape, 1), device=input_ids.device)


def main() -> int:
    common.verify_upstream()
    items, item_to_id = common.load_catalog()
    assert len(items) == common.N_EXPECTED_ITEMS
    assert min(item_to_id.values()) == 1 and max(item_to_id.values()) == common.N_EXPECTED_ITEMS

    dataset = common.PrefixTrainDataset([[1, 2, 3], [2, 3]])
    assert len(dataset) == 5
    _, first_input, first_answer = dataset[0]
    assert int(first_answer) == 1 and int(first_input.sum()) == 0
    _, third_input, third_answer = dataset[2]
    assert int(third_answer) == 3 and third_input[-2:].tolist() == [1, 2]
    _, fourth_input, fourth_answer = dataset[3]
    assert int(fourth_answer) == 2 and int(fourth_input.sum()) == 0

    source = inspect.getsource(common.load_train_valid)
    assert 'verify_split("test")' not in source.lower()
    assert "load_test_targets" not in source

    device = torch.device("cpu")
    model = DummyModel()
    summary, records = common.evaluate(
        model,
        histories=[[1], [1, 2]],
        targets=[2, 3],
        n_items=3,
        device=device,
        keep_records=True,
    )
    assert records is not None
    # User 0: item 3 strictly beats target 2 => rank 1. User 1: target 3 => rank 0.
    assert records["rank0"].tolist() == [1, 0]
    expected_ndcg = (1.0 / math.log2(3.0) + 1.0) / 2.0
    assert abs(float(summary["NDCG@10"]) - expected_ndcg) < 1e-12
    assert summary["n_eval"] == 2 and summary["HR@10"] == 1.0

    common.set_seed(123)
    wearec = common.build_model("official_sports", 8)
    sample = torch.tensor([[0] * 48 + [1, 2]], dtype=torch.long)
    output = wearec(sample)
    assert tuple(output.shape) == (1, 50, 64)
    assert np.isfinite(output.detach().numpy()).all()
    unused = torch.zeros(1, dtype=torch.long)
    loss = wearec.calculate_loss(sample, torch.tensor([3]), unused, unused, unused)
    loss.backward()
    assert math.isfinite(float(loss.detach()))
    print("WEARec V1 structural/conformance tests: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
