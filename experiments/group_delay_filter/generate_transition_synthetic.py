#!/usr/bin/env python3
"""Generate coupled synthetic sequences with controlled transition reuse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


SEED = 20260802
USERS = 2000
ITEMS = 2000
TOPICS = 10
TOPIC_SIZE = ITEMS // TOPICS
SEQUENCE_LENGTH = 62
CONDITIONS = {
    "SyntheticTransitionHigh": 0.85,
    "SyntheticTransitionLow": 0.15,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def generate_condition(
    alpha: float,
    permutations: np.ndarray,
    user_topics: np.ndarray,
    start_positions: np.ndarray,
    transition_draws: np.ndarray,
    noise_draws: np.ndarray,
) -> tuple[list[list[int]], int]:
    position_maps = [
        {int(item): position for position, item in enumerate(permutation)}
        for permutation in permutations
    ]
    topic_items = [sorted(int(item) for item in permutation) for permutation in permutations]
    sequences = []
    shared_steps = 0
    for user in range(USERS):
        topic = int(user_topics[user])
        permutation = permutations[topic]
        current = int(permutation[int(start_positions[user])])
        sequence = [current]
        seen = {current}
        for step in range(SEQUENCE_LENGTH - 1):
            if transition_draws[user, step] < alpha:
                position = position_maps[topic][current]
                for offset in range(1, TOPIC_SIZE + 1):
                    candidate = int(permutation[(position + offset) % TOPIC_SIZE])
                    if candidate not in seen:
                        break
                shared_steps += 1
            else:
                unseen = [item for item in topic_items[topic] if item not in seen]
                index = min(int(noise_draws[user, step] * len(unseen)), len(unseen) - 1)
                candidate = unseen[index]
            sequence.append(candidate)
            seen.add(candidate)
            current = candidate
        if len(sequence) != SEQUENCE_LENGTH or len(seen) != SEQUENCE_LENGTH:
            raise AssertionError("generator produced a repeated or missing item")
        sequences.append(sequence)
    return sequences, shared_steps


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    if not args.preregistration.exists():
        raise FileNotFoundError(args.preregistration)

    rng = np.random.Generator(np.random.PCG64(SEED))
    permutations = np.empty((TOPICS, TOPIC_SIZE), dtype=np.int64)
    for topic in range(TOPICS):
        items = np.arange(
            topic * TOPIC_SIZE + 1, (topic + 1) * TOPIC_SIZE + 1, dtype=np.int64
        )
        permutations[topic] = rng.permutation(items)
    user_topics = rng.integers(0, TOPICS, size=USERS)
    start_positions = rng.integers(0, TOPIC_SIZE, size=USERS)
    transition_draws = rng.random((USERS, SEQUENCE_LENGTH - 1))
    noise_draws = rng.random((USERS, SEQUENCE_LENGTH - 1))

    args.output_dir.mkdir(parents=True, exist_ok=True)
    records = {}
    for name, alpha in CONDITIONS.items():
        sequences, shared_steps = generate_condition(
            alpha,
            permutations,
            user_topics,
            start_positions,
            transition_draws,
            noise_draws,
        )
        output = args.output_dir / f"{name}.txt"
        with output.open("w", encoding="ascii") as handle:
            for user, sequence in enumerate(sequences):
                handle.write(f"{user} {' '.join(map(str, sequence))}\n")
        records[name] = {
            "alpha": alpha,
            "path": str(output.resolve()),
            "sha256": sha256(output),
            "shared_steps": shared_steps,
            "shared_step_fraction": shared_steps / (USERS * (SEQUENCE_LENGTH - 1)),
        }

    manifest = {
        "protocol": "COUPLED_SHARED_TRANSITION_SYNTHETIC_V1",
        "seed": SEED,
        "random_generator": "NumPy PCG64",
        "users": USERS,
        "items": ITEMS,
        "topics": TOPICS,
        "topic_size": TOPIC_SIZE,
        "sequence_length": SEQUENCE_LENGTH,
        "unique_items_per_sequence": SEQUENCE_LENGTH,
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
