"""Locked deterministic synthetic workload for the H10A performance preflight.

This module contains no filesystem access and no random generation.  The H10A
runner imports it lazily only for the ``self-test`` action.  The clean-room
verifier is required to reproduce these formulae independently.
"""

from __future__ import annotations

from typing import Any, Iterable


SCHEMA_VERSION = "h10a_synthetic_fixture.v1"
VIEW_ORDER = ("primary", "metadata_blocklist", "hub_removal")
ENDPOINT_ORDER = ("H", "C")
VIEW_BUDGETS = {
    "primary": {"relations": 110, "H_edges": 4481, "C_edges": 5529},
    "metadata_blocklist": {"relations": 105, "H_edges": 4388, "C_edges": 5104},
    "hub_removal": {"relations": 103, "H_edges": 3644, "C_edges": 4577},
}
EXPECTED_PROPOSALS = 4_774_300
EXPECTED_RETAINED_ENDPOINT_STATES = 280
EXPECTED_V_SCORE_PASSES = 280
EXPECTED_RANKING_SCORE_PASSES = 280
EXPECTED_PATTERNS = 812
EXPECTED_IMPRESSIONS = 8192
EXPECTED_CANDIDATE_OCCURRENCES = 290_648
EXPECTED_SUPPORTED_OCCURRENCES = 290_290
EXPECTED_CANDIDATE_ANCHOR_NONZEROS = 1_354_440
EXPECTED_USER_ANCHOR_NONZEROS = 32_768


def relation_id(relation_ordinal: int) -> str:
    if relation_ordinal < 0 or relation_ordinal >= 1000:
        raise ValueError("synthetic relation ordinal is outside S000..S999")
    return f"S{relation_ordinal:03d}"


def edge_count(total: int, relations: int, relation_ordinal: int) -> int:
    if total <= 0 or relations <= 0 or not 0 <= relation_ordinal < relations:
        raise ValueError("invalid synthetic edge allocation")
    quotient, remainder = divmod(total, relations)
    return quotient + int(relation_ordinal < remainder)


def relation_edges(
    view: str,
    endpoint: str,
    relation_ordinal: int,
) -> tuple[tuple[int, int], ...]:
    if view not in VIEW_BUDGETS or endpoint not in ENDPOINT_ORDER:
        raise ValueError("invalid synthetic graph key")
    budget = VIEW_BUDGETS[view]
    relations = int(budget["relations"])
    total = int(budget[f"{endpoint}_edges"])
    m = edge_count(total, relations, relation_ordinal)
    endpoint_ordinal = ENDPOINT_ORDER.index(endpoint)
    values: list[tuple[int, int]] = []
    for slot in range(m):
        if view == "hub_removal":
            row = 2 + ((slot + 7 * relation_ordinal + 3 * endpoint_ordinal) % 48)
        else:
            row = (slot + 7 * relation_ordinal + 3 * endpoint_ordinal) % 50
        column = (3 * slot + 11 * relation_ordinal + 5 * endpoint_ordinal) % 17
        values.append((row, column))
    if len(values) != len(set(values)):
        raise AssertionError("synthetic edge formula produced a duplicate")
    return tuple(values)


def pattern_anchors(pattern_id: int) -> tuple[int, ...]:
    if not 0 <= pattern_id < EXPECTED_PATTERNS:
        raise ValueError("synthetic pattern ID is outside 0..811")
    return tuple(bit for bit in range(10) if (pattern_id >> bit) & 1)


def candidate_count(impression_ordinal: int) -> int:
    if not 0 <= impression_ordinal < EXPECTED_IMPRESSIONS:
        raise ValueError("synthetic impression ordinal is outside 0..8191")
    return 11 + (impression_ordinal % 50)


def candidate_id(impression_ordinal: int, candidate_ordinal: int) -> str:
    count = candidate_count(impression_ordinal)
    if not 0 <= candidate_ordinal < count:
        raise ValueError("synthetic candidate ordinal is invalid")
    return f"SYN{impression_ordinal:04d}_{candidate_ordinal:02d}"


def user_anchors(impression_ordinal: int) -> tuple[int, ...]:
    if not 0 <= impression_ordinal < EXPECTED_IMPRESSIONS:
        raise ValueError("synthetic impression ordinal is outside 0..8191")
    return tuple((impression_ordinal + 13 * step) % 50 for step in range(4))


def iter_candidate_patterns() -> Iterable[tuple[int, int, int, str]]:
    occurrence = 0
    for impression in range(EXPECTED_IMPRESSIONS):
        for candidate in range(candidate_count(impression)):
            yield (
                occurrence,
                impression,
                occurrence % EXPECTED_PATTERNS,
                candidate_id(impression, candidate),
            )
            occurrence += 1
    if occurrence != EXPECTED_CANDIDATE_OCCURRENCES:
        raise AssertionError("synthetic candidate occurrence count mismatch")


def manifest_object() -> dict[str, Any]:
    return {
        "V_score_passes": EXPECTED_V_SCORE_PASSES,
        "candidate_anchor_nonzeros": EXPECTED_CANDIDATE_ANCHOR_NONZEROS,
        "candidate_count_formula": "11+(impression_ordinal mod 50)",
        "candidate_id_formula": "SYN{impression_ordinal:04d}_{candidate_ordinal:02d}",
        "candidate_occurrences": EXPECTED_CANDIDATE_OCCURRENCES,
        "candidate_pattern_formula": "global_occurrence mod 812",
        "edge_allocation": "floor(M/R)+1 for relation ordinal < M mod R; floor(M/R) otherwise",
        "edge_column_formula": "(3*t+11*r+5*endpoint_ordinal) mod 17",
        "edge_row_formula": "(t+7*r+3*endpoint_ordinal) mod 50",
        "endpoint_ordinals": {"C": 1, "H": 0},
        "hub_row_formula": "2+((t+7*r+3*endpoint_ordinal) mod 48)",
        "impressions": EXPECTED_IMPRESSIONS,
        "news_patterns": EXPECTED_PATTERNS,
        "pattern_formula": "distinct ten-bit masks p=0..811 over anchors 0..9",
        "proposals": EXPECTED_PROPOSALS,
        "ranking_score_passes": EXPECTED_RANKING_SCORE_PASSES,
        "relation_id_formula": "S000 onward",
        "retained_endpoint_states": EXPECTED_RETAINED_ENDPOINT_STATES,
        "schema_version": SCHEMA_VERSION,
        "supported_candidate_occurrences": EXPECTED_SUPPORTED_OCCURRENCES,
        "target_columns_per_relation": 17,
        "user_anchor_nonzeros": EXPECTED_USER_ANCHOR_NONZEROS,
        "user_formula": "anchors (i+13*t) mod 50 for t=0..3, each value binary64 0.5",
        "views": {
            view: {
                "C_edges": int(VIEW_BUDGETS[view]["C_edges"]),
                "H_edges": int(VIEW_BUDGETS[view]["H_edges"]),
                "relations": int(VIEW_BUDGETS[view]["relations"]),
            }
            for view in VIEW_ORDER
        },
    }


def assert_manifest_counts() -> None:
    if EXPECTED_V_SCORE_PASSES != EXPECTED_RETAINED_ENDPOINT_STATES or EXPECTED_RANKING_SCORE_PASSES != EXPECTED_RETAINED_ENDPOINT_STATES:
        raise AssertionError("synthetic retained-state score-pass count mismatch")
    if sum(candidate_count(i) for i in range(EXPECTED_IMPRESSIONS)) != EXPECTED_CANDIDATE_OCCURRENCES:
        raise AssertionError("synthetic slate count formula mismatch")
    occurrences = EXPECTED_CANDIDATE_OCCURRENCES
    unsupported = 1 + (occurrences - 1) // EXPECTED_PATTERNS
    if occurrences - unsupported != EXPECTED_SUPPORTED_OCCURRENCES:
        raise AssertionError("synthetic supported occurrence count mismatch")
    nonzeros = 0
    for occurrence in range(occurrences):
        nonzeros += len(pattern_anchors(occurrence % EXPECTED_PATTERNS))
    if nonzeros != EXPECTED_CANDIDATE_ANCHOR_NONZEROS:
        raise AssertionError("synthetic candidate-anchor nonzero count mismatch")
    if EXPECTED_IMPRESSIONS * 4 != EXPECTED_USER_ANCHOR_NONZEROS:
        raise AssertionError("synthetic user-anchor nonzero count mismatch")
    for view in VIEW_ORDER:
        budget = VIEW_BUDGETS[view]
        for endpoint in ENDPOINT_ORDER:
            total = sum(
                len(relation_edges(view, endpoint, relation))
                for relation in range(int(budget["relations"]))
            )
            if total != int(budget[f"{endpoint}_edges"]):
                raise AssertionError("synthetic endpoint edge total mismatch")
