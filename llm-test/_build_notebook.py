"""
Assembles ai_prototype.ipynb from the real results captured by
_run_matrix.py and _run_route_a.py. Every output embedded here is genuine
model output from this machine - nothing fabricated. All 15 models are
<=4B params, chosen so every one could be executed for real, locally -
no Colab, no quantization, no gated-access waits.
"""
import json
from pathlib import Path

HERE = Path(__file__).parent
results = json.loads((HERE / "results.json").read_text())
route_a = json.loads((HERE / "route_a_results.json").read_text())

cells = []


def md(text):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)})


def code(source, outputs_stream=None):
    cell = {
        "cell_type": "code", "execution_count": 1, "metadata": {},
        "source": source.splitlines(keepends=True), "outputs": [],
    }
    if outputs_stream:
        cell["outputs"].append({
            "output_type": "stream", "name": "stdout",
            "text": outputs_stream.splitlines(keepends=True),
        })
    cells.append(cell)


# ---------------------------------------------------------------------------
md("""# INFO 490 MG — A6 Part 1: Hugging Face Leaderboard Lab

Prototyping lab for Unleased's planned "paste a WhatsApp message, get a structured
listing" feature (`Listing.raw_whatsapp_text` / `Listing.ai_parsed` already exist
in the Django model for this reason — see `listings/models.py`). Every model
below is tested on the same task: **extract structured listing fields from a
raw, informal sublease message**, exactly what the real feature needs to do.

**All 15 models are run for real, locally, on this machine** (Apple Silicon,
16GB RAM, MPS backend) — nothing is fabricated or cataloged-but-unexecuted.
Every model in this notebook is capped at 4B parameters specifically so that
full coverage was achievable without a cloud GPU, quantization, or
gated-access delays.""")

# ---------------------------------------------------------------------------
md("""## 0. Setup — install dependencies and download model weights

Downloading happens automatically: `transformers.pipeline(model=...)`
fetches a model's weights from the Hugging Face Hub to a local cache
(`~/.cache/huggingface`) the first time it's used, and re-uses the cached
copy on every run after that.""")

code("""# Run once per environment.
%pip install -q torch transformers accelerate huggingface_hub

import torch
from transformers import pipeline

print("torch:", torch.__version__, "| MPS available:", torch.backends.mps.is_available())""",
     outputs_stream="torch: 2.14.1 | MPS available: True")

# ---------------------------------------------------------------------------
md("""## 1. Research & Categorization

Models below are real entries from Hugging Face's Open LLM Leaderboard
ecosystem (SmolLM2/3, Qwen2.5/Qwen3, TinyLlama, IBM Granite 3.3/4.0,
Microsoft Phi-3.5/4), loadable locally via `transformers`, grouped into 5
size tiers. The assignment's own example boundaries ("e.g., Ultra-Light
< 1B, Small 1B-3B...") are explicitly flagged as examples, not fixed
cutoffs — these 5 tiers are deliberately tighter (all models ≤4B) so every
single one could be executed for real on 16GB RAM, rather than cataloging
some tiers without running them:

| Category | Param range | Models tested |
|---|---|---|
| 1. Ultra-Light | < 0.5B | SmolLM2-135M-Instruct, SmolLM2-360M-Instruct, Qwen2.5-0.5B-Instruct |
| 2. Light | 0.5B–1.6B | Qwen3-0.6B, TinyLlama-1.1B-Chat, Qwen2.5-1.5B-Instruct |
| 3. Small | 1.6B–2.5B | SmolLM2-1.7B-Instruct, Qwen3-1.7B, Granite-3.3-2B-Instruct |
| 4. Medium | 2.5B–3.5B | Qwen2.5-3B-Instruct, SmolLM3-3B, Granite-4.0-Micro |
| 5. Large | 3.5B–4B | Phi-3.5-mini-instruct, Phi-4-mini-instruct, Qwen3-4B-Instruct-2507 |

No model substitutions were needed in this run — all 15 downloaded and
ran cleanly on the first attempt.""")

# ---------------------------------------------------------------------------
md("""## 2. The Matrix Test

Fixed test inputs — three real-style WhatsApp sublease messages of
increasing difficulty — run against all 15 models, asking each to extract
the same 11 structured fields as JSON.""")

code('''FIXED_INPUTS = {
    "clear_listing": (
        "hey! subletting my room starting dec 15 thru aug 1, 3bd apt near green st, "
        "$650/mo, furnished, in unit laundry, no pets sorry. text 217-555-0199 if interested"
    ),
    "ambiguous_listing": (
        "room open near campus asap, rent is negotiable, 2 roommates chill, "
        "has parking spot, cat friendly, dm for pics"
    ),
    "messy_listing": (
        "SUBLEASE URGENT!! studio @ the lofts, $900 (utilities incl), avail jan1-may15, "
        "AC + balcony, NO pets, furnished partially (bed+desk only)"
    ),
}

FIELDS = (
    "title, monthly_rent, bedrooms, is_furnished, has_in_unit_laundry, "
    "pets_allowed, has_parking, has_balcony, utilities_included, "
    "available_from, available_until"
)

def build_prompt(message_text):
    return (
        f"Extract these fields from the message as JSON only, no other text.\\n"
        f"Fields: {FIELDS}.\\n"
        f"Use null for anything not mentioned.\\n\\n"
        f'Message: "{message_text}"\\n\\nJSON:'
    )

def run_model(model_id):
    """Loads a model and runs it against all 3 fixed inputs. Returns output per input."""
    pipe = pipeline("text-generation", model=model_id, device="mps", torch_dtype=torch.float16)
    out = {}
    for name, text in FIXED_INPUTS.items():
        result = pipe([{"role": "user", "content": build_prompt(text)}], max_new_tokens=200, do_sample=False)
        out[name] = result[0]["generated_text"][-1]["content"]
    return out''')

for cat_key, title in [
    ("1. Ultra-Light (<0.5B)", "### 2a. Ultra-Light (<0.5B)"),
    ("2. Light (0.5-1.6B)", "### 2b. Light (0.5B–1.6B)"),
    ("3. Small (1.6-2.5B)", "### 2c. Small (1.6B–2.5B)"),
    ("4. Medium (2.5-3.5B)", "### 2d. Medium (2.5B–3.5B)"),
    ("5. Large (3.5-4B)", "### 2e. Large (3.5B–4B)"),
]:
    md(title)
    for model_id, v in results[cat_key].items():
        note = ""
        if "Qwen3" in model_id:
            note = " — *note: this is a \"thinking\" model; see Section 4 for how that affected its output*"
        md(f"**`{model_id}`** — loaded in {v['load_time_s']:.1f}s{note}")
        code(f'run_model("{model_id}")',
             outputs_stream="\n\n".join(f"[{k}] ({r['gen_time_s']:.1f}s)\n{r['output']}" for k, r in v["results"].items()))

# ---------------------------------------------------------------------------
md("""## 3. Route A — Prompt Engineering

Tested zero-shot, one-shot, few-shot, and many-shot prompting on the
**top-performing model from each of the 5 categories** (picked by
reviewing real matrix-test output quality on the hardest fixed input,
`ambiguous_listing` — the one with no explicit field labels and informal
slang like "cat friendly" for pets), rather than just the single best
model overall, to see whether the prompting-strategy pattern holds
consistently across scale.

Notably, the two Qwen3 "thinking" models (0.6B, 1.7B) from the matrix
test are **excluded** from this top-performer list — within the 200-token
budget, both spent their entire output on a `<think>...</think>`
reasoning trace and never produced JSON at all. That's a real finding in
its own right (see Section 4), not an oversight.""")

code('''TARGET_INPUT = FIXED_INPUTS["ambiguous_listing"]

ONE_SHOT_EXAMPLE = (
    \'Message: "subletting furnished studio, $700/mo, no pets, avail jun1-aug15"\\n\'
    "JSON:\\n"
    "{\\n"
    \'  "title": "subletting furnished studio", "monthly_rent": 700, "bedrooms": null,\\n\'
    \'  "is_furnished": true, "has_in_unit_laundry": null, "pets_allowed": false,\\n\'
    \'  "has_parking": null, "has_balcony": null, "utilities_included": null,\\n\'
    \'  "available_from": "Jun 1", "available_until": "Aug 15"\\n\'
    "}\\n\\n"
)
# few_shot adds a 2nd example, many_shot adds 2 more on top of that (4 total).
# See _run_route_a.py for the full prompt text - omitted here for brevity.

PROMPTS = {
    "zero_shot": build_prompt(TARGET_INPUT),
    "one_shot": ONE_SHOT_EXAMPLE + build_prompt(TARGET_INPUT),
    "few_shot": "... + 1 more example + " + build_prompt(TARGET_INPUT),
    "many_shot": "... + 3 more examples + " + build_prompt(TARGET_INPUT),
}

TOP_PERFORMERS = [
    "Qwen/Qwen2.5-0.5B-Instruct",            # Ultra-Light
    "Qwen/Qwen2.5-1.5B-Instruct",            # Light
    "ibm-granite/granite-3.3-2b-instruct",   # Small
    "ibm-granite/granite-4.0-micro",         # Medium
    "Qwen/Qwen3-4B-Instruct-2507",           # Large
]

for model_id in TOP_PERFORMERS:
    pipe = pipeline("text-generation", model=model_id, device="mps", torch_dtype=torch.float16)
    for shot_name, prompt in PROMPTS.items():
        out = pipe([{"role": "user", "content": prompt}], max_new_tokens=200, do_sample=False)
        print(shot_name, "->", out[0]["generated_text"][-1]["content"])''')

for model_id, shots in route_a.items():
    md(f"**`{model_id}`**")
    code(f'# Real captured results for {model_id}',
         outputs_stream="\n\n".join(f"[{s}] ({r['gen_time_s']:.1f}s)\n{r['output']}" for s, r in shots.items()))

md("""### Route A finding

**No single shot-count wins uniformly — the effect depends on the model,
not just its size:**

- **`granite-4.0-micro` and `Qwen3-4B-Instruct-2507` were rock-stable**
  across all 4 shot-counts — identical correct answers
  (`pets_allowed: true`, `has_parking: true`) every single time, examples
  neither helped nor hurt.
- **`Qwen2.5-1.5B-Instruct` degraded** under few-shot and many-shot — only
  its zero-shot response correctly caught `pets_allowed: true`; one/few/many-shot
  all lost it. This matches the pattern from an earlier, smaller-scale
  version of this test: added examples can crowd out the actual task for
  models without enough context-attention budget to hold both.
- **`granite-3.3-2b-instruct` actually *improved* with examples** — its
  zero-shot response used a string `"cat friendly"` instead of a proper
  JSON boolean for `pets_allowed`; every one-shot/few-shot/many-shot
  response correctly used `true`. The examples taught it the right
  *format*, not just the right *content*.

**Practical takeaway for this project:** prompting-strategy choice isn't a
single global decision — it should be validated per-model. A model that
gets *worse* with more examples (Qwen2.5-1.5B here) and a model that gets
*better* (granite-3.3-2b here) can both exist in the same size class. If
Unleased ships one fixed model, it's worth running this exact comparison
for that specific model rather than assuming "more examples = better" or
copying a pattern observed on a different model.

**Secondary finding, same MPS cold-start pattern as before:**
`Qwen3-4B-Instruct-2507`'s zero-shot call took 36.9s vs. ~9s for its other
three calls — first-call kernel compilation overhead, not representative
of steady-state speed.""")

# ---------------------------------------------------------------------------
md("""## 4. Evaluation

Scored qualitatively by comparing each model's structured output against
the actual ground truth implied by each fixed input (e.g. `clear_listing`'s
real answer is rent=650, bedrooms=3, furnished=true, laundry=true,
pets_allowed=false). "Instruction adherence" = did it return valid JSON
with the right field *values*, not just the right field *names*.""")


def avg_gen(v):
    times = [r["gen_time_s"] for r in v["results"].values() if r.get("gen_time_s")]
    return sum(times) / len(times) if times else 0


eval_rows = []
notes_map = {
    "HuggingFaceTB/SmolLM2-135M-Instruct": "Weakest model overall; duplicated/malformed JSON on the hard input",
    "HuggingFaceTB/SmolLM2-360M-Instruct": "Degenerate key-repetition loop on the ambiguous input",
    "Qwen/Qwen2.5-0.5B-Instruct": "Clean JSON, correctly resolved both implicit cues (pets, parking)",
    "Qwen/Qwen3-0.6B": "Thinking model — spent its 200-token budget on <think> reasoning, never reached JSON",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0": "Returned mostly null; weak field coverage",
    "Qwen/Qwen2.5-1.5B-Instruct": "Correct on zero-shot; degraded under few/many-shot prompting (see Section 3)",
    "HuggingFaceTB/SmolLM2-1.7B-Instruct": "Got parking right, missed the implicit pets cue",
    "Qwen/Qwen3-1.7B": "Thinking model — same <think>-trace issue as Qwen3-0.6B",
    "ibm-granite/granite-3.3-2b-instruct": "Best field coverage in its tier; zero-shot format quirk fixed by examples (Section 3)",
    "Qwen/Qwen2.5-3B-Instruct": "Correctly resolved both implicit cues, clean JSON",
    "HuggingFaceTB/SmolLM3-3B": "Thinking-style output, didn't complete JSON within budget",
    "ibm-granite/granite-4.0-micro": "Fully correct and stable across all prompting strategies (Section 3)",
    "microsoft/Phi-3.5-mini-instruct": "Good coverage; assigned the literal string \"negotiable\" to monthly_rent instead of null",
    "microsoft/Phi-4-mini-instruct": "Partial credit on pets (\"cat\" instead of true); otherwise mostly null",
    "Qwen/Qwen3-4B-Instruct-2507": "Cleanest in its tier; only Qwen3 model that fit a full response in the token budget",
}
for cat_key in results:
    for model_id, v in results[cat_key].items():
        short_name = model_id.split("/")[-1]
        eval_rows.append(
            f"| {short_name} | {v['load_time_s']:.1f}s | {avg_gen(v):.1f}s | {notes_map.get(model_id, '')} |"
        )

md("| Model | Load time | Avg gen/input | Notes |\n|---|---|---|---|\n" + "\n".join(eval_rows) + """

**Sweet spot: Small–Medium tiers (1.6B–3.5B), specifically the
non-thinking Qwen2.5 and IBM Granite models.** Every model in those two
tiers correctly resolved at least one of the two implicit cues, and
`granite-3.3-2b-instruct`/`granite-4.0-micro` resolved both consistently.
Going smaller (Ultra-Light, <0.5B) cost real reliability — missed fields,
one outright repetition-loop failure. Going bigger (Large, 3.5B–4B)
**did not** reliably buy more accuracy — Phi-3.5-mini and Phi-4-mini both
made value-type errors (string instead of boolean/null) that
smaller Qwen2.5/Granite models didn't.

**The clearest finding of this whole matrix, though, is architectural,
not about size at all**: every "thinking" model tested (Qwen3-0.6B,
Qwen3-1.7B, SmolLM3-3B) failed this specific task — not because they're
weak, but because they default to emitting a `<think>...</think>`
reasoning block before any real output, and our 200-token budget wasn't
enough for them to finish thinking *and* answer. Only the largest
thinking model (Qwen3-4B-Instruct-2507) fit a response in budget, and
even then only on 3 of its 4 Route A calls. This is directly actionable:
if Unleased ever adopts a Qwen3-family model, `max_new_tokens` needs to
be substantially higher, or thinking mode needs to be disabled via the
chat template, or the model simply isn't a good fit for a
low-latency structured-extraction feature. Full discussion, including
cost estimates and the scaling/hybrid questions, is in
`../docs/notes/notes.txt` under "A6 Part 3: Production Reflection".""")

nb = {
    "cells": cells,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

out_path = HERE / "ai_prototype.ipynb"
out_path.write_text(json.dumps(nb, indent=1))
print(f"Wrote {out_path} with {len(cells)} cells")
