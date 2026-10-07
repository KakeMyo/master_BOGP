from __future__ import annotations

from typing import Sequence

import numpy as np


def warmup_headroom(hypervolumes: Sequence[float], warmup: int = 18) -> dict:
    """Finite-budget improvement timing, NOT a proof of true convergence."""
    hv = np.asarray(hypervolumes, dtype=float)
    if len(hv) <= warmup or not np.all(np.isfinite(hv)):
        raise ValueError("A finite HV series including the warm-up boundary is required.")
    best = np.maximum.accumulate(hv)
    gain = float(best[-1] - best[0])
    q = float((best[warmup] - best[0]) / gain) if gain > 1e-12 else None
    t90 = int(np.flatnonzero(best >= best[0] + 0.9 * gain - 1e-12)[0]) if gain > 1e-12 else None
    return {
        "hv_initial": float(hv[0]), "hv_warmup": float(hv[warmup]), "hv_final": float(hv[-1]),
        "post_warmup_hv_gain_raw": float(hv[-1] - hv[warmup]),
        "post_warmup_hv_gain_running_max": float(best[-1] - best[warmup]),
        "warmup_improvement_fraction": q, "t90_finite_budget": t90,
        "post_warmup_hv_time_mean": float(np.mean(hv[warmup + 1:])),
        "late_hv_gain_running_max_60_to_end": float(best[-1] - best[min(60, len(best) - 1)]),
        "hv_decrease_count": int(np.sum(np.diff(hv) < -1e-12)),
    }
