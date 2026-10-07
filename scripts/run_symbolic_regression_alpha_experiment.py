from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/private/tmp/bogp_mpl_cache")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from bogp.formal_experiment import (  # noqa: E402
    FixedRateMethodConfig,
    FormalExperimentConfig,
    run_registered_experiment,
)


def main() -> int:
    run_id = "ver_alpha_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    problem_names = ("sr_alpha_friedman", "sr_alpha_poly10")
    summaries = []
    for problem_name in problem_names:
        config = FormalExperimentConfig(
            problem_name=problem_name,
            seeds=(0, 1, 2),
            population_size=24,
            total_generations=30,
            archive_size=200,
            archive_structure_key_mode="topology_value",
            fixed_rate_methods=(
                FixedRateMethodConfig(
                    name="plain_fixed",
                    crossover_rate=0.80,
                    mutation_rate=0.05,
                ),
            ),
            include_bogp_current=True,
            output_root=str(ROOT / "outputs" / "symbolic_regression_alpha"),
            run_id=run_id,
        )
        result = run_registered_experiment(config)
        summaries.append(
            {
                "problem_name": problem_name,
                "output_dir": str(result.output_dir),
                "summary_by_seed_path": str(result.summary_by_seed_path),
                "aggregate_summary_path": str(result.aggregate_summary_path),
                "run_count": len(result.run_summaries),
            }
        )

    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
