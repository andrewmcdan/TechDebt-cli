from __future__ import annotations
import math
from typing import Dict


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_score(components: Dict[str, float], weights: Dict[str, float]) -> float:
    wsum = 0.0
    for k, v in components.items():
        w = weights.get(k, 0.0)
        wsum += w * v
    return round(100.0 * sigmoid(wsum), 2)


def bucket(score: float) -> str:
    if score >= 70.0:
        return "P1"
    if score >= 40.0:
        return "P2"
    return "P3"