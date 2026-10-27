"""
Merges Part 1's real benchmarking notebook (../a7/a7_part1_benchmark.ipynb)
with Part 2/3's notebook (multi_model_system.ipynb, built by
_build_notebook.py) into one final combined file, matching the
assignment's deliverable spec: ONE notebook containing experiments,
benchmarking, and scaling simulations.

Part 1's cells are copied as-is (including their real, already-executed
outputs from the teammate's actual Colab run) - nothing in Part 1 is
re-run or re-typed here.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent

part1 = json.loads((HERE / "../a7/a7_part1_benchmark.ipynb").read_text())
part23 = json.loads((HERE / "multi_model_system.ipynb").read_text())

divider = {
    "cell_type": "markdown",
    "metadata": {},
    "source": [
        "---\n",
        "\n",
        "# Part 2 & Part 3\n",
        "\n",
        "Everything above this line is Part 1 (real benchmarking, unedited from\n",
        "the teammate's actual Colab T4 GPU run). Everything below reuses that\n",
        "same real data for cost modeling and routing simulation.\n",
    ],
}

merged_cells = part1["cells"] + [divider] + part23["cells"]

merged = {
    "cells": merged_cells,
    "metadata": part23["metadata"],
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = HERE / "multi_model_system.ipynb"
out_path.write_text(json.dumps(merged, indent=1))
print(f"Merged {len(part1['cells'])} (Part 1) + 1 (divider) + {len(part23['cells'])} (Part 2/3) "
      f"= {len(merged_cells)} cells -> {out_path}")
