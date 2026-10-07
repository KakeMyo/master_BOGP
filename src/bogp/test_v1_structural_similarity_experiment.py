from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
import random
from statistics import mean, stdev
from typing import Iterable, List, Sequence

from .diversity import (
    TreeNodeToken,
    structural_diversity,
    structural_similarity,
    subtree_hash_counter,
)


@dataclass(frozen=True)
class SimilarityExperimentConfig:
    max_m: int = 24
    unique_count_a: int = 8
    unique_count_b: int = 10
    one_sided_fixed_m: int = 8
    random_trials: int = 40
    random_background_children: int = 4
    random_background_depth: int = 3
    random_seed: int = 7


@dataclass(frozen=True)
class SimilarityRow:
    experiment: str
    m: int
    trial: int
    similarity: float
    diversity: float
    intersection: int
    union: int
    theory_similarity: float
    tree_size_a: int
    tree_size_b: int

    def to_dict(self) -> dict:
        return asdict(self)


def multiset_jaccard(counter_a: Counter, counter_b: Counter) -> tuple[float, int, int]:
    intersection = sum((counter_a & counter_b).values())
    union = sum(counter_a.values()) + sum(counter_b.values()) - intersection
    if union <= 0:
        return (1.0, intersection, union)
    return (intersection / union, intersection, union)


def motif_tokens() -> List[TreeNodeToken]:
    return [
        TreeNodeToken("shared_motif", 2),
        TreeNodeToken("shared_left", 0),
        TreeNodeToken("shared_right", 0),
    ]


def _motif_hash_count() -> int:
    return sum(subtree_hash_counter(motif_tokens()).values())


def _repeated_motifs(count: int) -> List[TreeNodeToken]:
    tokens: List[TreeNodeToken] = []
    for _ in range(count):
        tokens.extend(motif_tokens())
    return tokens


def build_controlled_tree(
    side: str,
    shared_motif_count: int,
    unique_leaf_count: int,
) -> List[TreeNodeToken]:
    tokens = [TreeNodeToken(f"{side}_root", shared_motif_count + unique_leaf_count)]
    tokens.extend(
        TreeNodeToken(f"{side}_unique_{index}", 0)
        for index in range(unique_leaf_count)
    )
    tokens.extend(_repeated_motifs(shared_motif_count))
    return tokens


def _counter_stats(tree_a: Iterable[TreeNodeToken], tree_b: Iterable[TreeNodeToken]) -> tuple[int, int]:
    counter_a = subtree_hash_counter(tree_a)
    counter_b = subtree_hash_counter(tree_b)
    _, intersection, union = multiset_jaccard(counter_a, counter_b)
    return (intersection, union)


def _tree_row(
    experiment: str,
    m: int,
    trial: int,
    tree_a: Sequence[TreeNodeToken],
    tree_b: Sequence[TreeNodeToken],
    theory_similarity: float,
) -> SimilarityRow:
    similarity = structural_similarity(tree_a, tree_b)
    diversity = structural_diversity(tree_a, tree_b)
    intersection, union = _counter_stats(tree_a, tree_b)
    return SimilarityRow(
        experiment=experiment,
        m=m,
        trial=trial,
        similarity=similarity,
        diversity=diversity,
        intersection=intersection,
        union=union,
        theory_similarity=theory_similarity,
        tree_size_a=len(tree_a),
        tree_size_b=len(tree_b),
    )


def run_ideal_multiset_experiment(
    config: SimilarityExperimentConfig,
) -> List[SimilarityRow]:
    rows: List[SimilarityRow] = []
    q = _motif_hash_count()
    for m in range(config.max_m + 1):
        counter_a = Counter({f"a_unique_{index}": 1 for index in range(config.unique_count_a)})
        counter_b = Counter({f"b_unique_{index}": 1 for index in range(config.unique_count_b)})
        for hash_index in range(q):
            counter_a[f"shared_{hash_index}"] += m
            counter_b[f"shared_{hash_index}"] += m

        similarity, intersection, union = multiset_jaccard(counter_a, counter_b)
        theory = (m * q) / (config.unique_count_a + config.unique_count_b + (m * q))
        rows.append(
            SimilarityRow(
                experiment="ideal_multiset",
                m=m,
                trial=0,
                similarity=similarity,
                diversity=1.0 - similarity,
                intersection=intersection,
                union=union,
                theory_similarity=theory,
                tree_size_a=sum(counter_a.values()),
                tree_size_b=sum(counter_b.values()),
            )
        )
    return rows


def run_shared_tree_experiment(
    config: SimilarityExperimentConfig,
) -> List[SimilarityRow]:
    rows: List[SimilarityRow] = []
    q = _motif_hash_count()
    unique_overhead = config.unique_count_a + config.unique_count_b + 2
    for m in range(config.max_m + 1):
        tree_a = build_controlled_tree("a", m, config.unique_count_a)
        tree_b = build_controlled_tree("b", m, config.unique_count_b)
        theory = (m * q) / (unique_overhead + (m * q))
        rows.append(_tree_row("shared_tree", m, 0, tree_a, tree_b, theory))
    return rows


def run_one_sided_experiment(
    config: SimilarityExperimentConfig,
) -> List[SimilarityRow]:
    rows: List[SimilarityRow] = []
    q = _motif_hash_count()
    fixed_m = config.one_sided_fixed_m
    unique_overhead = config.unique_count_a + config.unique_count_b + 2
    tree_a = build_controlled_tree("a", fixed_m, config.unique_count_a)
    for m in range(config.max_m + 1):
        tree_b = build_controlled_tree("b", m, config.unique_count_b)
        theory = (min(fixed_m, m) * q) / (
            unique_overhead + (max(fixed_m, m) * q)
        )
        rows.append(_tree_row("one_sided_tree", m, 0, tree_a, tree_b, theory))
    return rows


def _random_unique_subtree(
    rng: random.Random,
    side: str,
    depth: int,
    serial: list[int],
) -> List[TreeNodeToken]:
    node_id = serial[0]
    serial[0] += 1

    if depth <= 0 or rng.random() < 0.35:
        return [TreeNodeToken(f"{side}_rand_leaf_{node_id}", 0)]

    arity = 1 if rng.random() < 0.25 else 2
    tokens = [TreeNodeToken(f"{side}_rand_op_{node_id}", arity)]
    for _ in range(arity):
        tokens.extend(_random_unique_subtree(rng, side, depth - 1, serial))
    return tokens


def build_random_background_tree(
    side: str,
    shared_motif_count: int,
    rng: random.Random,
    background_children: int,
    background_depth: int,
) -> List[TreeNodeToken]:
    root_arity = shared_motif_count + background_children
    tokens = [TreeNodeToken(f"{side}_random_root", root_arity)]
    tokens.extend(_repeated_motifs(shared_motif_count))
    serial = [0]
    for _ in range(background_children):
        tokens.extend(_random_unique_subtree(rng, side, background_depth, serial))
    return tokens


def run_random_background_experiment(
    config: SimilarityExperimentConfig,
) -> List[SimilarityRow]:
    rows: List[SimilarityRow] = []
    q = _motif_hash_count()
    rng = random.Random(config.random_seed)
    for m in range(config.max_m + 1):
        for trial in range(config.random_trials):
            tree_a = build_random_background_tree(
                "a",
                m,
                rng,
                config.random_background_children,
                config.random_background_depth,
            )
            tree_b = build_random_background_tree(
                "b",
                m,
                rng,
                config.random_background_children,
                config.random_background_depth,
            )
            unique_overhead = (len(tree_a) - (m * q)) + (len(tree_b) - (m * q))
            theory = (m * q) / (unique_overhead + (m * q))
            rows.append(_tree_row("random_background", m, trial, tree_a, tree_b, theory))
    return rows


def run_all_experiments(config: SimilarityExperimentConfig) -> List[SimilarityRow]:
    rows: List[SimilarityRow] = []
    rows.extend(run_ideal_multiset_experiment(config))
    rows.extend(run_shared_tree_experiment(config))
    rows.extend(run_one_sided_experiment(config))
    rows.extend(run_random_background_experiment(config))
    return rows


def is_non_decreasing(values: Sequence[float], tolerance: float = 1e-12) -> bool:
    return all(
        right + tolerance >= left
        for left, right in zip(values, values[1:])
    )


def summarize_rows(rows: Sequence[SimilarityRow], config: SimilarityExperimentConfig) -> dict:
    by_experiment: dict[str, List[SimilarityRow]] = {}
    for row in rows:
        by_experiment.setdefault(row.experiment, []).append(row)

    ideal = sorted(by_experiment.get("ideal_multiset", []), key=lambda row: row.m)
    shared = sorted(by_experiment.get("shared_tree", []), key=lambda row: row.m)
    one_sided = sorted(by_experiment.get("one_sided_tree", []), key=lambda row: row.m)
    random_rows = by_experiment.get("random_background", [])

    random_means = []
    for m in range(config.max_m + 1):
        values = [row.similarity for row in random_rows if row.m == m]
        if values:
            random_means.append(mean(values))

    one_sided_peak = max(one_sided, key=lambda row: row.similarity) if one_sided else None
    max_ideal_error = max(
        (abs(row.similarity - row.theory_similarity) for row in ideal),
        default=0.0,
    )

    random_std_max = 0.0
    for m in range(config.max_m + 1):
        values = [row.similarity for row in random_rows if row.m == m]
        if len(values) >= 2:
            random_std_max = max(random_std_max, stdev(values))

    return {
        "config": asdict(config),
        "motif_hash_count": _motif_hash_count(),
        "row_count": len(rows),
        "ideal_matches_theory_max_abs_error": max_ideal_error,
        "ideal_similarity_non_decreasing": is_non_decreasing([row.similarity for row in ideal]),
        "shared_tree_similarity_non_decreasing": is_non_decreasing(
            [row.similarity for row in shared]
        ),
        "one_sided_peak_m": one_sided_peak.m if one_sided_peak is not None else None,
        "one_sided_fixed_m": config.one_sided_fixed_m,
        "random_mean_similarity_non_decreasing": is_non_decreasing(random_means),
        "random_similarity_max_std": random_std_max,
    }
