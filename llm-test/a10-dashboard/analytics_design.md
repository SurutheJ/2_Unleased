# Analytics Dashboard — Part 1: Analytics Design

This design is for the AI listing assistant (`listings/ai_assistant`
view, documented in full in `README_AI.md`): a local Hugging Face model
(`granite-4.0-micro`) extracts structured listing fields from a pasted
sublease message, an optional Gemini API call writes a short description,
and the user can turn the result into a real `Listing` via "Create listing
from this." Every question below is grounded in that real pipeline and its
actual code paths (status codes, validation rules, model choice), not
invented metrics with no system behind them.

## Step 1: Questions

### 1. System performance

1. **How does end-to-end latency split between the local model step and the
   optional Gemini API step, and how much of total latency is one-time model
   loading vs. steady-state inference?** `README_AI.md` already measured this
   once by hand (~16-21s cold start, ~7-9s per message after) — the dashboard
   should show this continuously instead of as a one-off manual measurement.
2. **What fraction of requests end in each outcome — success (200), rejected
   as too short (400), rejected as suspicious/injection (400), unparseable
   model output (422), model unavailable (503), or rate-limited (429) — and
   is that mix stable over time?** A rising 422/503 rate would mean the
   model or its environment is degrading.
3. **How does latency vary with input length (message character count), and
   are there slow outliers worth investigating?** Mean latency hides whether
   a few long/unusual messages are dragging the user experience down for a
   subset of requests.

### 2. User behavior

1. **Of the 11 extractable fields, how many does a typical request actually
   fill in (`found_count`), and how does that distribution look — mostly
   complete messages, mostly sparse ones, or bimodal?** This tells us whether
   users are pasting genuinely detailed posts or mostly vague ones.
2. **Which individual fields get blanked by the grounding check most often
   (e.g. `is_furnished`, `has_balcony`), and does that match the known
   failure mode documented in `README_AI.md` §2 (ungrounded boolean
   hallucination)?** If one field is blanked constantly, that's a concrete
   signal of where the model is weakest on real traffic, not just on our 5
   hand-picked test messages.
3. **What fraction of previews actually convert into a saved listing via
   "Create listing from this," versus being abandoned after the preview?**
   This is the feature's real success metric — extraction quality is only
   useful if people act on it.

### 3. Cost

1. **What is the real cost per request, split into local-model compute cost
   and (optional) Gemini API cost?** The local model has no per-token API
   fee, but it isn't free either — it occupies compute time that has a real
   dollar cost at scale, using the same $/machine-hour reasoning A7's cost
   model (`llm-test/a7-part2-3/cost_model.py`) already built for this
   project's other models.
2. **How does projected monthly cost scale across the same traffic tiers A7
   already defined (Prototype → Global Platform), using this feature's own
   measured latency and the real Hugging Face/Together AI pricing A7 already
   sourced?** This reuses real numbers instead of re-deriving pricing from
   scratch.
3. **What fraction of requests actually reach the paid Gemini call versus
   falling back to the free template description** (missing key, quota hit,
   timeout, blocked reply)? Today the key often isn't set and the free tier
   has hit its daily quota in real testing (`README_AI.md` §3), so the
   *true* paid-API surface area may be much smaller than "every request
   calls an external API" would suggest.

## Step 2: Dashboard Planning

### Widgets

| Widget | Type |
|---|---|
| Latency over time | Line chart |
| Latency breakdown (local model vs. Gemini) | Stacked bar chart |
| Request outcome mix (200/400/422/429/503) | Bar chart |
| Fields-extracted distribution (`found_count`, 0-11) | Histogram |
| Most-blanked fields | Horizontal bar chart (ranked) |
| Preview → listing conversion rate | Summary metric (single number / gauge) |
| Cost per request (compute + API, split) | Summary metric |
| Projected monthly cost by traffic tier | Bar chart |
| Paid vs. free (template fallback) request share | Pie / donut chart |

### Question → widget map

| Question | Widget(s) | Data required |
|---|---|---|
| Perf Q1 (latency breakdown) | Latency breakdown stacked bar + latency-over-time line | Per-request timestamps for: request start, local-model-done, Gemini-call-done, response-sent |
| Perf Q2 (outcome mix) | Request outcome mix bar | Per-request HTTP status code / outcome label |
| Perf Q3 (latency vs. input length) | Latency-over-time line, colored/sized by message length (or a small scatter) | Per-request latency + cleaned message character count |
| Behavior Q1 (fields found distribution) | Fields-extracted histogram | Per-request `found_count` (already computed in `ai_assistant` view as `context['found_count']`) |
| Behavior Q2 (most-blanked fields) | Most-blanked fields bar | Per-request list of which of the 11 fields were blanked by `validate_fields`'s grounding check, aggregated by field name |
| Behavior Q3 (conversion rate) | Conversion summary metric | Count of previews generated vs. count of listings saved with `ai_parsed=True` (already a real field on `Listing`) |
| Cost Q1 (cost per request) | Cost-per-request summary metric | Per-request latency (compute-seconds) × $/machine-hour (from A7's `cost_model.py`), plus Gemini token count × Gemini per-token price when the API was actually called |
| Cost Q2 (projected cost by tier) | Cost-by-tier bar chart | This feature's own measured tokens/latency fed into A7's existing `TRAFFIC_TIERS` + `PER_MACHINE_HOURLY_USD` constants |
| Cost Q3 (paid vs. free share) | Paid/free donut chart | Per-request flag: `description.source == 'gemini'` vs `'fallback'` (already returned by `ai_external.generate_description`, so no new field needs to be invented) |

### Data source plan

No request-level logging exists yet in `listings/ai_local.py` /
`listings/ai_external.py` — the view is currently stateless (it renders a
result and optionally stores a draft in the session, nothing more). For Part
2, the plan is:
- Add a small, real request log (either a lightweight `AIRequestLog` model
  or an append-only CSV/JSON log file) written once per request from inside
  `ai_assistant()`, capturing: timestamp, outcome, latency (local model vs.
  Gemini split), message length, `found_count`, which fields were blanked,
  `description.source`, and whether a listing was later created from that
  draft.
- Seed it with **real logs** generated by actually using the app repeatedly
  (reusing the same approach as `llm-test/a9-eval/run_eval.py`, which
  already runs real requests through the real pipeline and records real
  latency), supplemented with **simulated data** only to fill in volume the
  real local testing can't produce (e.g., a Mass Consumer App's millions of
  daily requests needed for the cost-by-tier chart) — clearly labeled as
  simulated wherever it's used, per the assignment's own allowance for
  simulated data.

## Step 3: Data Science Thinking (Lightweight)

- **Central tendency, chosen deliberately**: median latency, not just mean,
  because the one-time model-loading cold start (~16-21s) is a real outlier
  that would skew a mean upward and misrepresent typical request speed;
  reporting both (median for "typical," mean or p95 for "worst case users
  actually hit") is more honest than either alone.
- **Distributions, not just averages**: a histogram of `found_count` and of
  latency, because two very different underlying patterns (most messages
  are detailed vs. most messages are vague; most requests are fast vs. a
  long tail of slow ones) both average out to the same mean but need
  different responses.
- **Trends over time**: latency and outcome-mix plotted chronologically, to
  catch degradation (e.g., Gemini's daily quota resetting and the
  paid/free split shifting predictably within a day — already observed
  informally in `README_AI.md` §3's real quota-exhaustion testing).
- **Comparisons across groups**: outcome mix and latency compared across
  categorical groups that already exist in the code — status code, which
  field was blanked, `description.source` (gemini vs. fallback) — rather
  than inventing arbitrary buckets.
- **A simple correlation check**: message length vs. latency, and message
  length vs. `found_count`, to see whether longer messages are genuinely
  slower/more informative or whether that's not actually true in practice.
- No modeling beyond this is needed or planned — the point is to describe
  what the system is actually doing with real aggregate statistics, not to
  predict or classify anything new.
