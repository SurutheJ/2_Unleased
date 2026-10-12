"""
A5 Part 3.4 — Alternative use #3: statistical analysis in a notebook.

This is the plain-Python mirror of use3_notebook_stats.ipynb — same code,
cell by cell, so it can be verified outside Jupyter too. It pulls the same
public API as use1_python_script.py, but instead of just printing counts,
it computes a 95% confidence interval for the proportion of listings that
are "Available" (the normal approximation to the binomial, same idea as a
political poll's margin of error).

Run with:
    python use3_notebook_stats.py
"""

import math
import requests

PUBLIC_API_URL = "https://parulmudaliar.pythonanywhere.com/listings/api/by-status/"


def main():
    rows = requests.get(PUBLIC_API_URL, timeout=10).json()
    by_status = {row["status"]: row["total"] for row in rows}

    n = sum(by_status.values())
    available = by_status.get("Available", 0)
    p_hat = available / n if n else 0.0

    # Standard error of a sample proportion, normal approximation:
    # SE = sqrt(p_hat * (1 - p_hat) / n)
    se = math.sqrt(p_hat * (1 - p_hat) / n) if n else 0.0
    z_95 = 1.96
    margin = z_95 * se
    ci_low, ci_high = max(0.0, p_hat - margin), min(1.0, p_hat + margin)

    print(f"Sample: n = {n} listings, pulled live from {PUBLIC_API_URL}")
    print(f"Counts by status: {by_status}\n")
    print(f"p_hat (proportion Available) = {p_hat:.3f}")
    print(f"Standard error               = {se:.3f}")
    print(f"95% confidence interval      = [{ci_low:.3f}, {ci_high:.3f}]")
    print(
        f"\nInterpretation: if the current listing mix is a snapshot of a "
        f"stable process, we'd expect the true share of 'Available' listings "
        f"to fall within [{ci_low:.1%}, {ci_high:.1%}] 95% of the time. The "
        f"interval is wide because n={n} is small — more listings would "
        f"narrow it."
    )


if __name__ == "__main__":
    main()
