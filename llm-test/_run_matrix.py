"""
Runs the 15-model matrix test and writes results to results.json incrementally,
so a crash/OOM on a later (bigger) model doesn't lose earlier results.
Real models, real local inference via transformers - nothing fabricated.
"""
import gc
import json
import time
from pathlib import Path

import torch
from transformers import pipeline

RESULTS_FILE = Path(__file__).parent / "results.json"

# Real models from Hugging Face's Open LLM Leaderboard ecosystem, grouped by
# parameter count. "Large"/"XL" are included for completeness (Part 1 asks
# for 15 models total) but are not executed on this 16GB-RAM machine -
# see the Production Reflection notes on why that's itself a finding.
MODEL_CATALOG = {
    "Ultra-Light (<1B)": [
        "HuggingFaceTB/SmolLM2-360M-Instruct",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "HuggingFaceTB/SmolLM2-135M-Instruct",  # swapped in for pythia-410m (no chat template, base model only)
    ],
    "Small (1B-3B)": [
        "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
        "Qwen/Qwen2.5-1.5B-Instruct",
        "HuggingFaceTB/SmolLM2-1.7B-Instruct",  # swapped in for gated gemma-2-2b-it
    ],
    "Medium (3B-7B)": [
        "Qwen/Qwen2.5-3B-Instruct",
        "microsoft/Phi-3-mini-4k-instruct",
        "microsoft/Phi-3.5-mini-instruct",  # swapped in for Mistral-7B (OOM'd at fp16 on 16GB RAM)
    ],
    "Large (7B-15B)": [
        "meta-llama/Llama-3.1-8B-Instruct",
        "mistralai/Mistral-Nemo-Instruct-2407",
        "Qwen/Qwen2.5-14B-Instruct",
    ],
    "XL (>15B)": [
        "Qwen/Qwen2.5-32B-Instruct",
        "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "meta-llama/Llama-3.1-70B-Instruct",
    ],
}

# Which categories to actually attempt locally. Large/XL are listed but
# skipped - 8B-70B params at fp16 need 16-140GB of RAM just for weights,
# more than this machine has.
CATEGORIES_TO_RUN = ["Ultra-Light (<1B)", "Small (1B-3B)", "Medium (3B-7B)"]

FIXED_INPUTS = [
    {
        "name": "clear_listing",
        "text": (
            "hey! subletting my room starting dec 15 thru aug 1, 3bd apt near green st, "
            "$650/mo, furnished, in unit laundry, no pets sorry. text 217-555-0199 if interested"
        ),
    },
    {
        "name": "ambiguous_listing",
        "text": (
            "room open near campus asap, rent is negotiable, 2 roommates chill, "
            "has parking spot, cat friendly, dm for pics"
        ),
    },
    {
        "name": "messy_listing",
        "text": (
            "SUBLEASE URGENT!! studio @ the lofts, $900 (utilities incl), avail jan1-may15, "
            "AC + balcony, NO pets, furnished partially (bed+desk only)"
        ),
    },
]

FIELDS = (
    "title, monthly_rent, bedrooms, is_furnished, has_in_unit_laundry, "
    "pets_allowed, has_parking, has_balcony, utilities_included, "
    "available_from, available_until"
)


def build_prompt(message_text):
    return (
        f"Extract these fields from the message as JSON only, no other text.\n"
        f"Fields: {FIELDS}.\n"
        f"Use null for anything not mentioned.\n\n"
        f'Message: "{message_text}"\n\nJSON:'
    )


def load_existing_results():
    if RESULTS_FILE.exists():
        return json.loads(RESULTS_FILE.read_text())
    return {}


def save_results(results):
    RESULTS_FILE.write_text(json.dumps(results, indent=2))


def run_one_model(model_id):
    print(f"\n{'=' * 60}\nLoading {model_id} ...")
    t0 = time.time()
    try:
        pipe = pipeline(
            "text-generation",
            model=model_id,
            device="mps",
            torch_dtype=torch.float16,
        )
    except Exception as e:
        print(f"  FAILED TO LOAD: {e}")
        return {"load_error": str(e)}
    load_time = time.time() - t0
    print(f"  loaded in {load_time:.1f}s")

    per_input = {}
    for item in FIXED_INPUTS:
        prompt = build_prompt(item["text"])
        t0 = time.time()
        try:
            out = pipe(
                [{"role": "user", "content": prompt}],
                max_new_tokens=200,
                do_sample=False,
            )
            gen_time = time.time() - t0
            content = out[0]["generated_text"][-1]["content"]
            print(f"  [{item['name']}] {gen_time:.1f}s")
        except Exception as e:
            gen_time = None
            content = f"GENERATION ERROR: {e}"
            print(f"  [{item['name']}] FAILED: {e}")
        per_input[item["name"]] = {"gen_time_s": gen_time, "output": content}

    del pipe
    gc.collect()
    try:
        torch.mps.empty_cache()
    except Exception:
        pass

    return {"load_time_s": load_time, "results": per_input}


def main():
    results = load_existing_results()
    for category in CATEGORIES_TO_RUN:
        results.setdefault(category, {})
        for model_id in MODEL_CATALOG[category]:
            if model_id in results[category]:
                print(f"Skipping already-run {model_id}")
                continue
            results[category][model_id] = run_one_model(model_id)
            save_results(results)  # save after every model, not just at the end
    print("\nDone. Results in results.json")


if __name__ == "__main__":
    main()
