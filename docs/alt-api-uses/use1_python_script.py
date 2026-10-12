"""
A5 Part 3.4 — Alternative use #1: a standalone Python script.

Anyone — not just this Django project — can pull Unleased's public listing
data into their own script with nothing more than `requests` and the public
API URL below. No login, no API key, no knowledge of Django required.

Run with:
    python use1_python_script.py
"""

import requests

PUBLIC_API_URL = "https://parulmudaliar.pythonanywhere.com/listings/api/by-status/"


def main():
    response = requests.get(PUBLIC_API_URL, timeout=10)
    response.raise_for_status()
    rows = response.json()  # e.g. [{"status": "Available", "total": 4}, ...]

    total_listings = sum(row["total"] for row in rows)

    print(f"Fetched {len(rows)} status categories from {PUBLIC_API_URL}\n")
    print(f"{'Status':<12}{'Count':>8}{'Share':>10}")
    for row in rows:
        share = (row["total"] / total_listings * 100) if total_listings else 0
        print(f"{row['status']:<12}{row['total']:>8}{share:>9.1f}%")

    busiest = max(rows, key=lambda row: row["total"])
    print(f"\nTotal listings across all statuses: {total_listings}")
    print(f"Most common status: {busiest['status']} ({busiest['total']} listings)")


if __name__ == "__main__":
    main()
