from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any


def compact_text(value: str) -> str:
    return re.sub(r"[\W_]+", "", value.lower(), flags=re.UNICODE)


def simhash64(value: str) -> int:
    text = compact_text(value)
    tokens = [text[index : index + 2] for index in range(max(1, len(text) - 1))] or [text]
    vector = [0] * 64
    for token in tokens:
        digest = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
        for bit in range(64):
            vector[bit] += 1 if digest & (1 << bit) else -1
    result = 0
    for bit, score in enumerate(vector):
        if score >= 0:
            result |= 1 << bit
    return result


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left_root, right_root = self.find(left), self.find(right)
        if left_root != right_root:
            self.parent[right_root] = left_root


def cluster_near_duplicates(
    records: list[dict[str, Any]],
    *,
    max_hours: int = 48,
    max_hamming: int = 8,
) -> tuple[list[list[int]], list[dict[str, Any]]]:
    indexed = sorted(
        enumerate(records),
        key=lambda item: datetime.fromisoformat(item[1]["published_at"]),
    )
    fingerprints = [simhash64(record["title"] + " " + record.get("summary", "")) for record in records]
    union = UnionFind(len(records))
    band_buckets: dict[tuple[int, int], list[int]] = defaultdict(list)
    parsed_times = [datetime.fromisoformat(record["published_at"]) for record in records]
    matches: list[dict[str, Any]] = []

    for original_index, _ in indexed:
        fingerprint = fingerprints[original_index]
        threshold = parsed_times[original_index] - timedelta(hours=max_hours)
        candidates: set[int] = set()
        for band in range(4):
            key = (band, (fingerprint >> (band * 16)) & 0xFFFF)
            candidates.update(band_buckets[key])
        for candidate in candidates:
            if parsed_times[candidate] < threshold:
                continue
            distance = hamming_distance(fingerprint, fingerprints[candidate])
            if distance <= max_hamming:
                union.union(original_index, candidate)
                matches.append(
                    {"left": candidate, "right": original_index, "hamming_distance": distance}
                )
        for band in range(4):
            key = (band, (fingerprint >> (band * 16)) & 0xFFFF)
            band_buckets[key].append(original_index)

    groups: dict[int, list[int]] = defaultdict(list)
    for index in range(len(records)):
        groups[union.find(index)].append(index)
    clusters = [indices for indices in groups.values() if len(indices) > 1]
    return clusters, matches

