# System Design — Multi-Model AI Systems (A7, Parts 2 & 3)

This document is independent of the Django project (per the assignment's
own note) — it's an analysis of Unleased's AI use case, not code that runs
inside the web app. All numbers referenced here are computed in
`multi_model_system.ipynb` from real data: the 15-model, 25-prompt
benchmark from Part 1 (`benchmark_table_for_report.csv`, included alongside
this document — the same file Part 1's real Colab run produced), and
real current pricing fetched from huggingface.co/pricing and
together.ai/pricing (Oct 2026).

## Part 2: Cost Comparison and Infrastructure Planning

### Architecture being costed

Unleased's actual shipped AI feature (`listings/ai_local.py` +
`listings/ai_external.py`, A6 Part 2) is a 2-stage pipeline:

1. **Local model** (currently `ibm-granite/granite-4.0-micro`) extracts
   structured listing fields from a pasted sublease message.
2. **Gemini API** turns the validated fields into a short description,
   with an automatic fallback to a template if the API is unavailable.

Every cost figure below assumes this same pipeline, scaled up.

### Step 2.1 — Average tokens per request: 500

Derived from the real pipeline, not assumed:

| Stage | Input (tokens) | Output (tokens) |
|---|---|---|
| Local model | ~175 (real system prompt text) + ~35 (typical message) | **66.0** (real measured average for "Structured extraction" prompts, A7 Part 1, n=75) |
| Gemini API | ~90 (validated fields serialized into a prompt) | ~90 (estimated — a 2-3 sentence description; the real cap is 1024 via `GEMINI_MAX_OUTPUT_TOKENS`, but actual usage is far below that ceiling) |

Total ≈ 456 tokens/request, rounded to **500** for clean arithmetic in the
tables below.

### Step 2.2 — Total Daily Token Load

`Total Daily Token Load = Daily Active Users × 500`

| Tier | DAU | Total Daily Token Load |
|---|---|---|
| Prototype | 1,000 | 500,000 |
| Early Startup | 10,000 | 5,000,000 |
| Growing Product | 100,000 | 50,000,000 |
| Large Platform | 1,000,000 | 500,000,000 |
| Mass Consumer App | 10,000,000 | 5,000,000,000 |
| Global Platform | 100,000,000 | 50,000,000,000 |

### Step 2.3 — Hardware cost (local hosting)

Full 90-row table (15 models × 6 tiers): [`step2_3_hardware_cost.csv`](step2_3_hardware_cost.csv).

**Methodology, stated plainly:**
- Per-model throughput is the **real measured average tokens/sec** from
  A7 Part 1 (25 prompts per model, run on a real **Google Colab T4 GPU**,
  fp16, `device_map="cuda"` — see `load_model()` in
  `a7_part1_benchmark.ipynb` — unbatched, i.e. one request processed at
  a time, no production serving optimizations).
- Per-machine cost: **$0.50/hour** for 1× NVIDIA T4 (14GB) — real, current
  Hugging Face Inference Endpoints pricing (huggingface.co/pricing,
  fetched Oct 2026). T4 specifically, not a different GPU tier, because
  that's the exact hardware class Part 1 actually benchmarked on — the
  cost estimate uses the same GPU the throughput was measured on, rather
  than substituting a different one.
- `Machines Needed = ceil(Total Daily Token Load / (tokens/sec × 86,400))`,
  `Total Machine Cost = Machines Needed × $12.00/day`.

**Important caveat, not hidden:** these are **naive, unbatched** throughput
numbers. A real production deployment would use a serving stack (vLLM,
TGI, continuous batching) that processes many concurrent requests on the
same GPU far more efficiently than one-at-a-time — likely 10-50x higher
effective throughput. The hardware costs below are therefore a
**conservative upper bound**, not a realistic production estimate. The
numbers are still useful for the *comparison* with API pricing below,
because the API side has the same kind of caveat in the opposite
direction (see Step 2.4).

Range across all 90 rows: from the cheapest cell (fastest model ×
Prototype tier, 1 machine, $12.00/day) to the most expensive (slowest
model × Global Platform tier, tens of thousands of machines,
hundreds of thousands of dollars per day).

### Step 2.4 — Hugging Face Inference Provider cost comparison

Full 90-row table: [`step2_4_api_cost.csv`](step2_4_api_cost.csv).

Real, current per-token pricing from **Together AI**, listed as a
Hugging Face Inference Provider:

| Local model category | Comparable hosted model | $/1M tokens | Note |
|---|---|---|---|
| Ultra-Light / Light / Small (<2.5B) | Llama 3 8B Instruct Lite | $0.14 | Extrapolated down — **no provider lists hosted pricing for sub-1B models**, which is itself a finding (see Analysis below) |
| Medium (2.5B–3.5B) | Qwen3.5 9B | $0.21 (avg of $0.17 in / $0.25 out) | Direct match, closest real size |
| Large (3.5B–4B) | Qwen2.5 7B Instruct Turbo | $0.30 | Direct match, closest real size |

### Step 2.5 — Analysis

**Direct comparison, real shipped model (`granite-4.0-micro`):**

| Tier | Local cost/day | API cost/day | Cheaper |
|---|---|---|---|
| Prototype | $12.00 | $0.10 | API |
| Early Startup | $48.00 | $1.05 | API |
| Growing Product | $408.00 | $10.50 | API |
| Large Platform | $4,044.00 | $105.00 | API |
| Mass Consumer App | $40,428.00 | $1,050.00 | API |
| Global Platform | $404,256.00 | $10,500.00 | API |

**At what scale is local hosting cheaper?** Under these assumptions:
**never, within the 6 modeled tiers.** This is a real, honest result, not
a hedge — but it needs its actual cause explained, not just reported:

1. **Fixed-cost floor.** A single cloud T4 GPU machine costs $12.00/day
   whether it serves 1 request or 10,000. At Prototype scale (1,000
   users), `granite-4.0-micro` only needs **one** machine — but even that
   single machine's $12.00/day floor is ~120x the API's $0.10/day for the
   same traffic. The gap is largest exactly where traffic is lowest,
   because the API has **no minimum** — you pay only for tokens actually
   used — while self-hosting can't bill for less than one full machine.
2. **Unbatched throughput.** Our local numbers measure one request at a
   time. A real production GPU server batches dozens of concurrent
   requests, multiplying effective throughput. We didn't benchmark that
   (A7 Part 1 explicitly measured single-request latency), so our local
   cost is realistically too high relative to what a properly-engineered
   self-hosted deployment would actually cost.

**At what scale is API usage cheaper?** Under our modeled assumptions:
**at every scale tested**, for the reason above. The gap *narrows* as
scale increases (local cost grows roughly linearly with traffic once
you're past the fixed-floor region, same as API cost) — but it never
crosses over within 100M DAU.

**When would you switch your architecture?** Not purely a function of
DAU count — it's a function of **effective batched throughput vs. API
price**, which our benchmark didn't measure. A real decision would need:
(a) re-benchmarking with a batching-capable serving stack to get a
realistic self-hosted tokens/sec figure, (b) comparing *that* number's
implied cost-per-million-tokens against the API's $0.14–$0.30/1M, and
(c) factoring in things this model doesn't capture at all — data
residency requirements, the API's rate limits, or wanting to fine-tune a
model's behavior beyond what prompting can reach (Unleased's own A6 Route
B fine-tuning experiment is exactly this kind of reason to self-host
regardless of raw per-token cost).

## Part 3: Multi-Model Routing Strategy

### Step 3.1 — Five real scenarios for Unleased

Grounded in the actual project, not generic textbook examples:

| # | Scenario | Description |
|---|---|---|
| 1 | **Normal operation** | Everyday sublease-message parsing — current default traffic shape, current default model. |
| 2 | **Peak move-out season** | UIUC leases mostly turn over in May and August; a flood of sublease posts arrives in a short window, unlike A7's flat daily-average assumption. |
| 3 | **High-complexity / garbled input** | A message that's longer, messier, or more ambiguous than the three A6/A7 test cases (e.g. a multi-unit listing pasted with several roommates' preferences mixed together). |
| 4 | **Cost-sensitive operation** | Unleased is a student project with no revenue — every Gemini API call is a real cost against a tight or zero budget, unlike a funded startup. |
| 5 | **External API degraded or exhausted** | Gemini's free-tier daily quota is hit, or the API is slow/down — this is not hypothetical, it's **already a real, coded path** in `listings/ai_external.py`. |

### Step 3.2 — Routing strategy per scenario

| Scenario | Routing Strategy | Local Model(s) Used | Hugging Face Model Used | Expected Benefit |
|---|---|---|---|---|
| 1. Normal operation | Single fixed path: local extraction → Gemini description. No routing decision needed — this is the simple default case routing *exists to protect*, not optimize. | `ibm-granite/granite-4.0-micro` | (same — hosted locally, not via HF Inference) | Simplicity; already the real shipped behavior. |
| 2. Peak move-out season | Route by **message length / system queue depth**: short, simple messages go to the fastest Ultra-Light model; longer or queued-up messages stay on the default model. | `Qwen/Qwen2.5-0.5B-Instruct` (fast path) + `ibm-granite/granite-4.0-micro` (default path) | — | Lower average latency during a real traffic spike, without permanently downgrading quality for every user. |
| 3. High-complexity / garbled input | Route by **heuristic complexity score** (message length above a threshold, or low local-model confidence from `validate_fields()`'s existing grounding checks): escalate to a Large-tier local model, or skip local entirely and let Gemini do extraction directly for the worst cases. | `microsoft/Phi-3.5-mini-instruct` (Large tier, better field coverage per A6/A7 findings) | Gemini (already integrated) as the escalation target | Better accuracy exactly where it's needed, without paying the Large-tier latency/cost cost on every request. |
| 4. Cost-sensitive operation | Route by **confidence + a cost ceiling**: skip the Gemini call entirely for routine, well-structured messages (template description instead); only spend the paid API call when the local extraction is ambiguous enough that a better description meaningfully helps, or quota remains. | `ibm-granite/granite-4.0-micro` (always) | Gemini, called conditionally, not unconditionally | Keeps real operating cost near zero most of the time, spending the limited paid quota where it matters most. |
| 5. External API degraded/exhausted | Route by **system health signal** (Gemini request failure, timeout, or a tracked daily quota counter): bypass the API path entirely and use the **already-implemented** template-description fallback. | `ibm-granite/granite-4.0-micro` + template fallback | Gemini (skipped on this path) | Zero downtime for the user-facing feature — this isn't a hypothetical improvement, it's formalizing real existing code (`ai_external.py`'s fallback) as an explicit routing policy. |

### Step 3.3 — Evaluating the strategies

**Latency.** Scenario 2's real measured effect (computed in
`multi_model_system.ipynb`, not assumed): routing 70% of peak traffic to
`Qwen2.5-0.5B-Instruct` (avg latency 2.01s, real A7 Part 1 measurement)
instead of always using `granite-4.0-micro` (avg 2.36s) saves **~10.3% of
total compute-time** at every traffic scale tested (1,000 to 10,000,000
DAU) — a modest but real win, because the two models' real measured
latencies are closer than intuition suggests. Scenario 3's escalation adds
latency only for the subset of requests that need it, rather than
slowing down every request to handle rare hard cases — the opposite
tradeoff from scaling the *default* model up.

**Cost.** Scenario 4 directly targets Step 2.5's finding: since the API
is cheaper than self-hosting at every scale we modeled, the real cost
lever isn't "local vs. API" in the abstract, it's **how often you call
the API at all.** Skipping Gemini for routine messages (template
description instead) cuts the per-request cost to just the local
model's compute — which, per Step 2.3, is itself non-trivial at scale, so
the actual biggest cost lever for Unleased is avoiding unnecessary calls
to *either* system, not just the paid one.

**Quality.** Scenario 3's escalation path exists because A6/A7 already
measured real quality differences across model sizes — Phi-3.5-mini had
better field coverage than smaller models on harder inputs, but smaller
models were just as good (sometimes better — see A6's `granite-3.3-2b`
finding) on easy ones. Routing by complexity means most users get a fast
response from a smaller model with *no quality loss*, because the smaller
model was already good enough for their case — quality is preserved by
sending each request to a model that's actually sufficient for it, not by
universally using the largest model "just in case."

**Net picture:** none of these five strategies trade quality for speed or
cost in the way a single global model-size choice would. Each routes
*around* a specific real constraint (burst traffic, hard input, budget,
API downtime) using a path that's already appropriate for that specific
condition — which is the actual argument for multi-model routing over
a single fixed model, beyond just "routing is more sophisticated."
