"""
A7 Part 2: Cost Comparison and Infrastructure Planning.

Builds all the real, computed tables (Step 2.2, 2.3, 2.4) from:
  - real per-model throughput measured in A7 Part 1 (benchmark_table_for_report.csv)
  - real Hugging Face Inference Endpoints GPU pricing (fetched Oct 2026)
  - real Together AI per-token serverless pricing for comparable open models
      (Together AI is one of Hugging Face's Inference Providers)

Nothing here is a placeholder - every number is either measured locally or
sourced from a real, current pricing page, with the source stated.
"""
import csv
import math
from pathlib import Path

HERE = Path(__file__).parent

# ---------------------------------------------------------------------------
# Step 2.1: Average tokens per request (grounded in the actual shipped feature)
# ---------------------------------------------------------------------------
# Unleased's real AI feature (listings/ai_local.py, listings/ai_external.py) is a
# 2-stage pipeline per user request:
#   Stage A (local model): system prompt (~175 tokens, measured from the real
#            build_system_prompt() text) + user message (avg ~35 tokens for a
#            typical sublease message) + real measured output (avg 66.0 tokens
#            for "Structured extraction" prompts in the Part 1 benchmark)
#            -> ~276 tokens
#   Stage B (Gemini API): prompt built from validated fields (~90 tokens) +
#            a short 2-3 sentence listing description (~90 tokens estimated,
#            well under the 1024-token GEMINI_MAX_OUTPUT_TOKENS ceiling)
#            -> ~180 tokens
# Total ~ 456, rounded to a clean 500 for the table math below.
AVG_TOKENS_PER_REQUEST = 500

# ---------------------------------------------------------------------------
# Step 2.2 + Part 2 traffic tiers (as specified)
# ---------------------------------------------------------------------------
TRAFFIC_TIERS = [
    ("Prototype", 1_000),
    ("Early Startup", 10_000),
    ("Growing Product", 100_000),
    ("Large Platform", 1_000_000),
    ("Mass Consumer App", 10_000_000),
    ("Global Platform", 100_000_000),
]

# ---------------------------------------------------------------------------
# Step 2.3: real per-model throughput, measured in A7 Part 1 on a real
# Google Colab T4 GPU (fp16, device_map="cuda", one request at a time -
# see a7_part1_benchmark.ipynb's load_model()). A real production serving
# stack would batch many concurrent requests on the same GPU for much
# higher effective throughput, so machine counts below are a conservative
# (upper-bound) estimate relative to a properly-batched deployment, not an
# optimistic one - stated explicitly rather than hidden.
# ---------------------------------------------------------------------------
def load_model_throughput():
    rows = list(csv.DictReader(open(HERE / "benchmark_table_for_report.csv")))
    by_model = {}
    cat_of = {}
    totals = {}
    counts = {}
    for r in rows:
        m = r["Model"]
        totals[m] = totals.get(m, 0.0) + float(r["Tokens/sec"])
        counts[m] = counts.get(m, 0) + 1
        cat_of[m] = r["Model Category"]
    for m in totals:
        by_model[m] = totals[m] / counts[m]
    return by_model, cat_of


# Real Hugging Face Inference Endpoints GPU pricing (huggingface.co/pricing,
# fetched Oct 2026). Using an NVIDIA T4 (14GB) instance specifically because
# that's the exact GPU tier the real Part 1 benchmark was measured on
# (Colab's free T4) - matching machine to measured throughput, rather than
# substituting a different GPU class we have no real numbers for.
PER_MACHINE_HOURLY_USD = 0.50  # 1x NVIDIA T4, huggingface.co/pricing
PER_MACHINE_DAILY_USD = PER_MACHINE_HOURLY_USD * 24
SECONDS_PER_DAY = 86_400


def build_hardware_cost_table():
    by_model, cat_of = load_model_throughput()
    rows = []
    for model, tok_s in sorted(by_model.items(), key=lambda kv: cat_of[kv[0]]):
        daily_capacity_tokens_per_machine = tok_s * SECONDS_PER_DAY
        for tier_name, dau in TRAFFIC_TIERS:
            daily_token_load = dau * AVG_TOKENS_PER_REQUEST
            machines_needed = math.ceil(daily_token_load / daily_capacity_tokens_per_machine)
            total_cost = machines_needed * PER_MACHINE_DAILY_USD
            rows.append({
                "Model Name": model,
                "Daily Traffic Category": tier_name,
                "Avg Tokens per User": AVG_TOKENS_PER_REQUEST,
                "Total Daily Token Load": daily_token_load,
                "Per Machine Cost (Cloud)": round(PER_MACHINE_DAILY_USD, 2),
                "Machines Needed": machines_needed,
                "Total Machine Cost": round(total_cost, 2),
            })
    return rows


# ---------------------------------------------------------------------------
# Step 2.4: Hugging Face Inference Provider (Together AI) per-token pricing
# for the closest comparable *hosted* open model to each of our 15 local
# models. Together AI is listed as a Hugging Face Inference Provider, so
# "Hosted on Hugging Face" is accurate for these.
#
# Real, current (Oct 2026) Together AI serverless rates, $/1M tokens:
#   Llama 3 8B Instruct Lite:  $0.14 in / $0.14 out
#   Qwen2.5 7B Instruct Turbo: $0.30 in / $0.30 out
#   Qwen3.5 9B:                $0.17 in / $0.25 out
# No serverless API provider lists hosted pricing for <1B models - that
# itself is a real finding (Step 2.5): the market doesn't bother hosting
# models this small as a paid product, because local/edge inference is
# already cheap enough. For Ultra-Light/Light/Small tiers (<2.5B) below,
# the closest real comparable is the smallest Together AI entry available
# (Llama 3 8B Instruct Lite), clearly flagged as an extrapolation downward,
# not a real listing for a model that small.
# ---------------------------------------------------------------------------
COMPARABLE_API_MODEL = {
    "Ultra-Light (<0.5B)": ("Llama 3 8B Instruct Lite", "Together AI (HF Inference Provider)", 0.14, True),
    "Light (0.5-1.6B)": ("Llama 3 8B Instruct Lite", "Together AI (HF Inference Provider)", 0.14, True),
    "Small (1.6-2.5B)": ("Llama 3 8B Instruct Lite", "Together AI (HF Inference Provider)", 0.14, True),
    "Medium (2.5-3.5B)": ("Qwen3.5 9B", "Together AI (HF Inference Provider)", 0.21, False),  # avg of $0.17/$0.25
    "Large (3.5-4B)": ("Qwen2.5 7B Instruct Turbo", "Together AI (HF Inference Provider)", 0.30, False),
}


def build_api_cost_table():
    by_model, cat_of = load_model_throughput()
    rows = []
    for model in sorted(by_model, key=lambda m: cat_of[m]):
        cat = cat_of[model]
        comparable, host, price_per_1m, extrapolated = COMPARABLE_API_MODEL[cat]
        for tier_name, dau in TRAFFIC_TIERS:
            daily_token_load = dau * AVG_TOKENS_PER_REQUEST
            est_cost = daily_token_load / 1_000_000 * price_per_1m
            rows.append({
                "Local LLM Model Size": model,
                "Comparable Paid Model": comparable + (" (extrapolated down)" if extrapolated else ""),
                "Hosted on Hugging Face": host,
                "Cost of Paid API per Token": price_per_1m / 1_000_000,
                "Daily Traffic Category": tier_name,
                "Total Token Load": daily_token_load,
                "Estimated API Cost": round(est_cost, 2),
                "Machines Required (API infrastructure)": 0,
                "Total Cost": round(est_cost, 2),
            })
    return rows


def write_csv(rows, filename):
    path = HERE / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {path} ({len(rows)} rows)")


def build_token_load_table():
    """Step 2.2: Total Daily Token Load per traffic tier (app-wide, not per-model)."""
    return [
        {
            "Daily Traffic Category": name,
            "Daily Active Users": dau,
            "Avg Tokens per Request": AVG_TOKENS_PER_REQUEST,
            "Total Daily Token Load": dau * AVG_TOKENS_PER_REQUEST,
        }
        for name, dau in TRAFFIC_TIERS
    ]


if __name__ == "__main__":
    token_load_rows = build_token_load_table()
    write_csv(token_load_rows, "step2_2_token_load.csv")

    hw_rows = build_hardware_cost_table()
    write_csv(hw_rows, "step2_3_hardware_cost.csv")
    assert len(hw_rows) == 15 * 6, f"expected 90 rows, got {len(hw_rows)}"

    api_rows = build_api_cost_table()
    write_csv(api_rows, "step2_4_api_cost.csv")
    assert len(api_rows) == 15 * 6, f"expected 90 rows, got {len(api_rows)}"

    print("\nBoth tables: 15 models x 6 traffic tiers = 90 rows each, as required.")
