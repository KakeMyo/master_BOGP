from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
from itertools import combinations
from math import isclose
from statistics import mean
from typing import Iterable, List, Sequence


@dataclass(frozen=True)
class TreeNodeToken:
    label: str
    arity: int


def _node_label(node) -> str:
    if isinstance(node, TreeNodeToken):
        return node.label
    if hasattr(node, "name"):
        return str(node.name)
    if hasattr(node, "value"):
        return repr(node.value)
    return str(node)


def _node_arity(node) -> int:
    if isinstance(node, TreeNodeToken):
        return node.arity
    return int(getattr(node, "arity", 0))


def to_prefix_tokens(tree: Iterable[object]) -> List[TreeNodeToken]:
    tokens: List[TreeNodeToken] = []
    for node in tree:
        tokens.append(TreeNodeToken(label=_node_label(node), arity=_node_arity(node)))
    return tokens


def _hash_subtree(
    tokens: Sequence[TreeNodeToken],
    index: int,
) -> tuple[int, bytes, Counter[bytes]]:
    token = tokens[index]
    next_index = index + 1
    child_hashes: List[bytes] = []
    counter: Counter[bytes] = Counter()

    for _ in range(token.arity):
        next_index, child_hash, child_counter = _hash_subtree(tokens, next_index)
        child_hashes.append(child_hash)
        counter.update(child_counter)

    hasher = hashlib.blake2b(digest_size=16)
    hasher.update(token.label.encode("utf-8"))
    hasher.update(b"|")
    hasher.update(str(token.arity).encode("ascii"))
    for child_hash in child_hashes:
        hasher.update(b":")
        hasher.update(child_hash)
    subtree_hash = hasher.digest()
    counter[subtree_hash] += 1
    return next_index, subtree_hash, counter


def subtree_hash_counter(tree: Iterable[object]) -> Counter[bytes]:
    tokens = to_prefix_tokens(tree)
    if not tokens:
        return Counter()

    next_index, _, counter = _hash_subtree(tokens, 0)
    if next_index != len(tokens):
        raise ValueError("Tree tokens do not form a valid prefix-encoded tree.")
    return counter


def structural_similarity(tree_a: Iterable[object], tree_b: Iterable[object]) -> float:
    counter_a = subtree_hash_counter(tree_a)
    counter_b = subtree_hash_counter(tree_b)
    size_a = sum(counter_a.values())
    size_b = sum(counter_b.values())
    if size_a == 0 and size_b == 0:
        return 1.0

    intersection = sum((counter_a & counter_b).values())
    union = size_a + size_b - intersection
    if union <= 0:
        return 1.0
    return intersection / union


def structural_diversity(tree_a: Iterable[object], tree_b: Iterable[object]) -> float:
    return 1.0 - structural_similarity(tree_a, tree_b)


def population_structural_diversity(
    population: Sequence[Iterable[object]],
    pair_sample_size: int | None = None,
) -> float:
    if len(population) <= 1:
        return 0.0

    counters = [subtree_hash_counter(tree) for tree in population]
    sizes = [sum(counter.values()) for counter in counters]
    pair_indices = list(combinations(range(len(population)), 2))
    if pair_sample_size is not None and pair_sample_size > 0 and len(pair_indices) > pair_sample_size:
        pair_indices = pair_indices[:pair_sample_size]

    diversities: List[float] = []
    for left, right in pair_indices:
        size_left = sizes[left]
        size_right = sizes[right]
        if size_left == 0 and size_right == 0:
            diversities.append(0.0)
            continue

        intersection = sum((counters[left] & counters[right]).values())
        union = size_left + size_right - intersection
        similarity = 1.0 if union <= 0 else (intersection / union)
        diversities.append(1.0 - similarity)

    return mean(diversities) if diversities else 0.0


def semantic_similarity(outputs_a: Sequence[float], outputs_b: Sequence[float]) -> float:
    if len(outputs_a) != len(outputs_b):
        raise ValueError("Semantic outputs must have the same length.")
    if len(outputs_a) == 0:
        return 1.0

    mean_a = mean(outputs_a)
    mean_b = mean(outputs_b)
    centered_a = [value - mean_a for value in outputs_a]
    centered_b = [value - mean_b for value in outputs_b]
    variance_a = sum(value * value for value in centered_a)
    variance_b = sum(value * value for value in centered_b)

    if isclose(variance_a, 0.0) and isclose(variance_b, 0.0):
        return 1.0
    if isclose(variance_a, 0.0) or isclose(variance_b, 0.0):
        return 0.0

    covariance = sum(left * right for left, right in zip(centered_a, centered_b))
    correlation = covariance / ((variance_a ** 0.5) * (variance_b ** 0.5))
    similarity = correlation * correlation
    if isclose(similarity, 1.0, rel_tol=1e-9, abs_tol=1e-9):
        return 1.0
    return max(0.0, min(1.0, similarity))


def semantic_diversity(outputs_a: Sequence[float], outputs_b: Sequence[float]) -> float:
    return 1.0 - semantic_similarity(outputs_a, outputs_b)
