#!/usr/bin/env python3
"""Generate coupled first- and second-order interleaved sequences."""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np


SEED = 20260803
USERS = 2000
ITEMS = 2000
TOPICS = 10
STREAM_SIZE = 100
USERS_PER_TOPIC = USERS // TOPICS
SEQUENCE_LENGTH = 62


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_sequences(
    stream_a: np.ndarray,
    stream_b: np.ndarray,
    user_topics: np.ndarray,
    starts_a: np.ndarray,
    starts_b: np.ndarray,
) -> list[list[int]]:
    sequences = []
    for user in range(USERS):
        topic = int(user_topics[user])
        start_a = int(starts_a[user])
        start_b = int(starts_b[user])
        sequence = []
        for offset in range(SEQUENCE_LENGTH // 2):
            sequence.append(int(stream_a[topic, (start_a + offset) % STREAM_SIZE]))
            sequence.append(int(stream_b[topic, (start_b + offset) % STREAM_SIZE]))
        if len(sequence) != SEQUENCE_LENGTH or len(set(sequence)) != SEQUENCE_LENGTH:
            raise AssertionError("generator produced a repeated or missing item")
        sequences.append(sequence)
    return sequences


def write_sequences(path: Path, sequences: list[list[int]]) -> None:
    with path.open("w", encoding="ascii") as handle:
        for user, sequence in enumerate(sequences):
            handle.write(f"{user} {' '.join(map(str, sequence))}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if not args.preregistration.exists():
        raise FileNotFoundError(args.preregistration)

    rng = np.random.Generator(np.random.PCG64(SEED))
    stream_a = np.empty((TOPICS, STREAM_SIZE), dtype=np.int64)
    stream_b = np.empty((TOPICS, STREAM_SIZE), dtype=np.int64)
    for topic in range(TOPICS):
        first = topic * 2 * STREAM_SIZE + 1
        stream_a[topic] = rng.permutation(
            np.arange(first, first + STREAM_SIZE, dtype=np.int64)
        )
        stream_b[topic] = rng.permutation(
            np.arange(first + STREAM_SIZE, first + 2 * STREAM_SIZE, dtype=np.int64)
        )

    user_topics = np.repeat(np.arange(TOPICS, dtype=np.int64), USERS_PER_TOPIC)
    rng.shuffle(user_topics)
    starts_a = np.empty(USERS, dtype=np.int64)
    starts_b = np.empty(USERS, dtype=np.int64)
    balanced_starts = np.tile(np.arange(STREAM_SIZE, dtype=np.int64), 2)
    for topic in range(TOPICS):
        users = np.flatnonzero(user_topics == topic)
        starts_a[users] = rng.permutation(balanced_starts)
        starts_b[users] = rng.permutation(balanced_starts)

    conditions = {
        "SyntheticCoupledPhase": make_sequences(
            stream_a, stream_b, user_topics, starts_a, starts_a
        ),
        "SyntheticIndependentPhase": make_sequences(
            stream_a, stream_b, user_topics, starts_a, starts_b
        ),
    }
    histograms = {
        name: collections.Counter(item for sequence in rows for item in sequence)
        for name, rows in conditions.items()
    }
    if histograms["SyntheticCoupledPhase"] != histograms["SyntheticIndependentPhase"]:
        raise AssertionError("condition item histograms differ")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, rows in conditions.items():
        output = args.output_dir / f"{name}.txt"
        write_sequences(output, rows)
        records[name] = {
            "path": str(output.resolve()),
            "sha256": sha256(output),
            "users": len(rows),
            "interactions": sum(map(len, rows)),
        }

    manifest = {
        "protocol": "COUPLED_HISTORY_DEPENDENCE_SYNTHETIC_V1",
        "seed": SEED,
        "random_generator": "NumPy PCG64",
        "users": USERS,
        "items": ITEMS,
        "topics": TOPICS,
        "stream_size": STREAM_SIZE,
        "sequence_length": SEQUENCE_LENGTH,
        "unique_items_per_sequence": SEQUENCE_LENGTH,
        "balanced_start_count_per_topic_stream": 2,
        "equal_item_histograms": True,
        "preregistration": str(args.preregistration.resolve()),
        "preregistration_sha256": sha256(args.preregistration),
        "generator_sha256": sha256(Path(__file__)),
        "conditions": records,
    }
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
