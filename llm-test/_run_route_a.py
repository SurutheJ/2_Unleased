"""
Route A: Prompt Engineering. Tests zero/one/few/many-shot prompting on the
top-performing models from the matrix test (one per category, 5 total),
against the hardest fixed input (ambiguous_listing). TOP_PERFORMERS is
filled in after the matrix test finishes and real quality is known.
"""
import json
import time
from pathlib import Path

import torch
from transformers import pipeline

RESULTS_FILE = Path(__file__).parent / "route_a_results.json"

# One best-performing model per category, picked by reviewing real matrix-test
# output quality on the hardest fixed input (ambiguous_listing). Notably, the
# Qwen3 "thinking" models (0.6B, 1.7B) are excluded here - they spent their
# 200-token budget on <think> reasoning and never produced JSON at all.
TOP_PERFORMERS = [
    "Qwen/Qwen2.5-0.5B-Instruct",       # Ultra-Light (<0.5B)
    "Qwen/Qwen2.5-1.5B-Instruct",       # Light (0.5-1.6B)
    "ibm-granite/granite-3.3-2b-instruct",  # Small (1.6-2.5B)
    "ibm-granite/granite-4.0-micro",    # Medium (2.5-3.5B)
    "Qwen/Qwen3-4B-Instruct-2507",      # Large (3.5-4B)
]

TARGET_INPUT = (
    "room open near campus asap, rent is negotiable, 2 roommates chill, "
    "has parking spot, cat friendly, dm for pics"
)

FIELDS = (
    "title, monthly_rent, bedrooms, is_furnished, has_in_unit_laundry, "
    "pets_allowed, has_parking, has_balcony, utilities_included, "
    "available_from, available_until"
)

BASE_INSTRUCTION = (
    f"Extract these fields from the message as JSON only, no other text.\n"
    f"Fields: {FIELDS}.\nUse null for anything not mentioned.\n\n"
)

ONE_SHOT_EXAMPLE = (
    'Message: "subletting furnished studio, $700/mo, no pets, avail jun1-aug15"\n'
    "JSON:\n"
    "{\n"
    '  "title": "subletting furnished studio", "monthly_rent": 700, "bedrooms": null,\n'
    '  "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": false,\n'
    '  "has_parking": null, "has_balcony": null, "utilities_included": null,\n'
    '  "available_from": "Jun 1", "available_until": "Aug 15"\n'
    "}\n\n"
)

FEW_SHOT_EXAMPLES = ONE_SHOT_EXAMPLE + (
    'Message: "2bd apt, pets ok, parking included, $1100/mo utilities incl, balcony"\n'
    "JSON:\n"
    "{\n"
    '  "title": "2bd apt", "monthly_rent": 1100, "bedrooms": 2,\n'
    '  "is_furnished": null, "has_in_unit_laundry": null, "pets_allowed": true,\n'
    '  "has_parking": true, "has_balcony": true, "utilities_included": true,\n'
    '  "available_from": null, "available_until": null\n'
    "}\n\n"
)

MANY_SHOT_EXAMPLES = FEW_SHOT_EXAMPLES + (
    'Message: "private room furnished no laundry no parking $500 avail now"\n'
    "JSON:\n"
    "{\n"
    '  "title": "private room", "monthly_rent": 500, "bedrooms": null,\n'
    '  "is_furnished": true, "has_in_unit_laundry": false, "pets_allowed": null,\n'
    '  "has_parking": false, "has_balcony": null, "utilities_included": null,\n'
    '  "available_from": "now", "available_until": null\n'
    "}\n\n"
    'Message: "5bd house 3 bath w/d in unit, huge balcony, dogs ok, $450/person"\n'
    "JSON:\n"
    "{\n"
    '  "title": "5bd house", "monthly_rent": 450, "bedrooms": 5,\n'
    '  "is_furnished": null, "has_in_unit_laundry": true, "pets_allowed": true,\n'
    '  "has_parking": null, "has_balcony": true, "utilities_included": null,\n'
    '  "available_from": null, "available_until": null\n'
    "}\n\n"
)


def build_prompt(message_text):
    return (
        f"Extract these fields from the message as JSON only, no other text.\n"
        f"Fields: {FIELDS}.\n"
        f"Use null for anything not mentioned.\n\n"
        f'Message: "{message_text}"\n\nJSON:'
    )


PROMPTS = {
    "zero_shot": BASE_INSTRUCTION + f'Message: "{TARGET_INPUT}"\n\nJSON:',
    "one_shot": BASE_INSTRUCTION + ONE_SHOT_EXAMPLE + f'Message: "{TARGET_INPUT}"\n\nJSON:',
    "few_shot": BASE_INSTRUCTION + FEW_SHOT_EXAMPLES + f'Message: "{TARGET_INPUT}"\n\nJSON:',
    "many_shot": BASE_INSTRUCTION + MANY_SHOT_EXAMPLES + f'Message: "{TARGET_INPUT}"\n\nJSON:',
}


def main():
    results = {}
    for model_id in TOP_PERFORMERS:
        print(f"\n{'=' * 60}\nLoading {model_id} ...")
        t0 = time.time()
        pipe = pipeline("text-generation", model=model_id, device="mps", torch_dtype=torch.float16)
        print(f"  loaded in {time.time() - t0:.1f}s")

        results[model_id] = {}
        for shot_name, prompt in PROMPTS.items():
            t0 = time.time()
            out = pipe([{"role": "user", "content": prompt}], max_new_tokens=200, do_sample=False)
            gen_time = time.time() - t0
            content = out[0]["generated_text"][-1]["content"]
            results[model_id][shot_name] = {"gen_time_s": gen_time, "output": content}
            print(f"  [{shot_name}] {gen_time:.1f}s")
            RESULTS_FILE.write_text(json.dumps(results, indent=2))

        del pipe

    print("\nDone. Results in route_a_results.json")


if __name__ == "__main__":
    main()
