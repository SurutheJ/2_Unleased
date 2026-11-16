"""
Aggregations for the AI analytics dashboard (A10 Part 2).

Everything here reads AIRequestLog and returns plain dicts/lists, so the same
numbers can feed the JSON API, the page's summary tiles and the tests.

Each widget answers one question from llm-test/a10-dashboard/analytics_design.md:
    performance: latency breakdown, outcome mix, latency vs input length
    behavior:    fields found, most-blanked fields, preview -> listing conversion
    cost:        cost per request, projected monthly cost by tier, paid vs free
"""
import math

from .models import AIRequestLog

FIELD_COUNT = 11   # extractable fields (listings.ai_local.FIELD_NAMES)

# --- Cost assumptions (from llm-test/a7-part2-3/cost_model.py and docs/notes/notes.txt) ---------
# Local model: no per-token fee, but it occupies a machine. A7 priced one NVIDIA T4 at $0.50/hour.
PER_MACHINE_HOURLY_USD = 0.50
SECONDS_PER_DAY = 86_400
DAYS_PER_MONTH = 30
# Gemini: price list of Gemini 3.1 Flash-Lite, $ per 1M tokens (looked up Oct 2026, see notes.txt).
# We do not record real token counts, so a description call is assumed to use the same
# token counts as the A6 production reflection: about 200 in and 500 out (hidden thinking included).
GEMINI_USD_PER_M_INPUT = 0.25
GEMINI_USD_PER_M_OUTPUT = 1.50
GEMINI_TOKENS_IN = 200
GEMINI_TOKENS_OUT = 500
# Same traffic tiers as A7; one assistant request per daily user is assumed.
TRAFFIC_TIERS = [
    ('Prototype', 1_000),
    ('Early Startup', 10_000),
    ('Growing Product', 100_000),
    ('Large Platform', 1_000_000),
    ('Mass Consumer App', 10_000_000),
    ('Global Platform', 100_000_000),
]

OUTCOME_LABELS = dict(AIRequestLog.Outcome.choices)
SOURCE_FILTERS = ('all', 'real', 'simulated')


def percentile(values, q):
    """Linear-interpolated percentile (q from 0 to 100); None for an empty list."""
    if not values:
        return None
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q / 100
    low, high = math.floor(pos), math.ceil(pos)
    return ordered[low] + (ordered[high] - ordered[low]) * (pos - low)


def pearson(xs, ys):
    """Pearson correlation of two equal-length lists; None if it is undefined."""
    n = len(xs)
    if n < 3:
        return None
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return None
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return cov / math.sqrt(var_x * var_y)


def _round(value, digits=2):
    return None if value is None else round(value, digits)


def gemini_cost_per_paid_request():
    return (GEMINI_TOKENS_IN * GEMINI_USD_PER_M_INPUT + GEMINI_TOKENS_OUT * GEMINI_USD_PER_M_OUTPUT) / 1_000_000


def build_metrics(source='all'):
    """All dashboard numbers as one JSON-serializable dict. source is 'all', 'real' or 'simulated'."""
    if source not in SOURCE_FILTERS:
        source = 'all'
    logs = AIRequestLog.objects.all()
    counts = {
        'real': logs.filter(is_simulated=False).count(),
        'simulated': logs.filter(is_simulated=True).count(),
    }
    if source == 'real':
        logs = logs.filter(is_simulated=False)
    elif source == 'simulated':
        logs = logs.filter(is_simulated=True)

    rows = list(logs.order_by('created_at'))
    ok = [r for r in rows if r.outcome == AIRequestLog.Outcome.SUCCESS]
    warm = [r for r in ok if not r.cold_start]
    cold = [r for r in ok if r.cold_start]

    # ---- Performance ----------------------------------------------------------------------
    totals_s = [r.total_ms / 1000 for r in ok]
    latency_over_time = [{
        'time': r.created_at.isoformat(), 'total_s': round(r.total_ms / 1000, 2),
        'local_s': round(r.local_ms / 1000, 2), 'gemini_s': round(r.gemini_ms / 1000, 2),
        'cold_start': 'Cold start (model loading)' if r.cold_start else 'Warm',
        'chars': r.message_chars, 'simulated': r.is_simulated,
    } for r in ok]

    def med(values):
        return _round(percentile(values, 50))

    breakdown = []
    for label, group in (('Cold start', cold), ('Warm request', warm)):
        if group:
            breakdown.append({'group': label, 'step': 'Local model', 'seconds': med([r.local_ms / 1000 for r in group]), 'requests': len(group)})
            # Gemini time is only meaningful when the call was attempted (a missing key skips it, gemini_ms = 0).
            called = [r.gemini_ms / 1000 for r in group if r.gemini_ms > 0]
            breakdown.append({'group': label, 'step': 'Gemini API step', 'seconds': med(called) or 0, 'requests': len(group),
                              'gemini_called': len(called)})

    outcome_counts = {key: 0 for key in OUTCOME_LABELS}
    for r in rows:
        outcome_counts[r.outcome] = outcome_counts.get(r.outcome, 0) + 1
    outcomes = [{'outcome': OUTCOME_LABELS[key], 'count': outcome_counts[key],
                 'share': _round(outcome_counts[key] / len(rows) * 100, 1) if rows else 0}
                for key in OUTCOME_LABELS]

    chars_vs_latency = pearson([r.message_chars for r in warm], [r.total_ms for r in warm])
    chars_vs_found = pearson([r.message_chars for r in ok], [r.found_count or 0 for r in ok])

    # ---- User behavior --------------------------------------------------------------------
    found_hist = [{'found': n, 'count': 0} for n in range(FIELD_COUNT + 1)]
    for r in ok:
        if r.found_count is not None and 0 <= r.found_count <= FIELD_COUNT:
            found_hist[r.found_count]['count'] += 1
    blank_counts = {}
    for r in ok:
        for name in r.blanked_fields or []:
            blank_counts[name] = blank_counts.get(name, 0) + 1
    blanked = [{'field': name, 'count': count, 'share': _round(count / len(ok) * 100, 1)}
               for name, count in sorted(blank_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    converted = sum(1 for r in ok if r.listing_created)

    # ---- Cost ----------------------------------------------------------------------------
    paid = [r for r in ok if r.description_source == 'gemini']
    free = [r for r in ok if r.description_source != 'gemini']
    paid_share = len(paid) / len(ok) if ok else 0
    mean_local_s = sum(r.local_ms for r in ok) / len(ok) / 1000 if ok else 0
    compute_per_request = mean_local_s / 3600 * PER_MACHINE_HOURLY_USD
    gemini_per_paid = gemini_cost_per_paid_request()
    blended_per_request = compute_per_request + paid_share * gemini_per_paid

    warm_local_s = percentile([r.local_ms / 1000 for r in warm], 50) or (mean_local_s or 0)
    tiers = []
    for name, requests_per_day in TRAFFIC_TIERS:
        machines = max(1, math.ceil(requests_per_day * warm_local_s / SECONDS_PER_DAY)) if warm_local_s else 0
        compute = machines * PER_MACHINE_HOURLY_USD * 24 * DAYS_PER_MONTH
        api = requests_per_day * DAYS_PER_MONTH * paid_share * gemini_per_paid
        tiers.append({'tier': name, 'requests_per_day': requests_per_day, 'machines': machines,
                      'cost_type': 'Local model machines', 'usd_per_month': round(compute, 2)})
        tiers.append({'tier': name, 'requests_per_day': requests_per_day, 'machines': machines,
                      'cost_type': 'Gemini API', 'usd_per_month': round(api, 2)})

    paid_free = [
        {'source': 'Gemini (paid API)', 'count': len(paid)},
        {'source': 'Template (free fallback)', 'count': len(free)},
    ]

    return {
        'filter': source,
        'counts': {**counts, 'total': counts['real'] + counts['simulated'], 'shown': len(rows)},
        'tiles': {
            'requests': len(rows),
            'success_rate': _round(len(ok) / len(rows) * 100, 1) if rows else None,
            'median_latency_s': med(totals_s),
            'p95_latency_s': _round(percentile(totals_s, 95)),
            'mean_latency_s': _round(sum(totals_s) / len(totals_s)) if totals_s else None,
            'median_found': med([r.found_count for r in ok if r.found_count is not None]),
            'conversion_rate': _round(converted / len(ok) * 100, 1) if ok else None,
            'paid_share': _round(paid_share * 100, 1) if ok else None,
        },
        'latency_over_time': latency_over_time,
        'breakdown': breakdown,
        'outcomes': outcomes,
        'correlations': {
            'chars_vs_latency': _round(chars_vs_latency),
            'chars_vs_found': _round(chars_vs_found),
            'warm_requests': len(warm),
        },
        'found_hist': found_hist,
        'blanked': blanked,
        'conversion': {'previews': len(ok), 'converted': converted,
                       'rate': _round(converted / len(ok) * 100, 1) if ok else None},
        'cost': {
            'compute_per_request_usd': round(compute_per_request, 6),
            'gemini_per_paid_request_usd': round(gemini_per_paid, 6),
            'blended_per_request_usd': round(blended_per_request, 6),
            'per_1000_requests_usd': round(blended_per_request * 1000, 2),
            'assumptions': {
                'machine_usd_per_hour': PER_MACHINE_HOURLY_USD,
                'gemini_tokens_in': GEMINI_TOKENS_IN, 'gemini_tokens_out': GEMINI_TOKENS_OUT,
                'gemini_usd_per_m_in': GEMINI_USD_PER_M_INPUT, 'gemini_usd_per_m_out': GEMINI_USD_PER_M_OUTPUT,
                'warm_local_seconds_used': _round(warm_local_s, 2),
            },
        },
        'tiers': tiers,
        'paid_free': paid_free,
    }
