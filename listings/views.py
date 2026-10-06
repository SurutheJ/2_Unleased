import csv
import json
import math
from io import BytesIO

import matplotlib
matplotlib.use('Agg')  # non-interactive backend: no display server needed, safe on any host
import matplotlib.pyplot as plt
import requests
import vl_convert

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.http import Http404
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.template import loader
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.models import UnleasedUser
from .models import Inquiry, Listing

# All four list views share ONE template. The views differ in how they fetch
# and pass the data; the page itself looks the same. `view_label` is only a
# small tag shown on the page so you can tell which view produced it.
LIST_TEMPLATE = 'listings/listing_list.html'


# ---------------------------------------------------------------------------
# Function-based views
# ---------------------------------------------------------------------------

def home(request):
    """
    Home page (/): a welcome header, the total number of listings,
    and the three newest listings that are still available.
    """
    context = {
        'featured': Listing.objects.filter(status=Listing.Status.AVAILABLE)[:3],
        'total_listings': Listing.objects.count(),
    }
    return render(request, 'listings/home.html', context)


def listing_manual(request):
    """FBV 1: load the template by hand and wrap the result in HttpResponse."""
    template = loader.get_template(LIST_TEMPLATE)
    context = {
        'listings': Listing.objects.select_related('lister'),
        'view_label': 'HttpResponse + loader.get_template()',
    }
    return HttpResponse(template.render(context, request))


def listing_render(request):
    """FBV 2: query the model and use the render() shortcut."""
    context = {
        'listings': Listing.objects.select_related('lister'),
        'view_label': 'render() shortcut',
    }
    return render(request, LIST_TEMPLATE, context)


# ---------------------------------------------------------------------------
# Class-based views
# ---------------------------------------------------------------------------

class ListingBaseView(View):
    """CBV 1: plain View; query the model manually inside get()."""

    def get(self, request):
        context = {
            'listings': Listing.objects.filter(status=Listing.Status.AVAILABLE),
            'view_label': 'Base CBV (View), available listings only',
        }
        return render(request, LIST_TEMPLATE, context)


class ListingListView(ListView):
    """CBV 2: generic ListView (its default template is listings/listing_list.html)."""
    model = Listing
    template_name = LIST_TEMPLATE
    context_object_name = 'listings'
    extra_context = {'view_label': 'Generic ListView'}


class ListingDetailView(DetailView):
    """
    Generic DetailView, adapted to also handle POST on the same URL
    (/listings/<pk>/):
      GET  -> the default DetailView behaviour: show the listing.
      POST -> create an Inquiry for the seeker who submitted the
              "Inquire about this listing" form on that page.

    This is real data modification (a new Inquiry row), so it goes through
    POST + {% csrf_token %}, not GET query params like listing_search().
    """
    model = Listing
    context_object_name = 'listing'

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        edu_email = request.POST.get('edu_email', '').strip().lower()
        message = request.POST.get('message', '').strip()

        error = ''
        sent = False
        seeker = UnleasedUser.objects.filter(edu_email__iexact=edu_email).first()

        if not edu_email.endswith('.edu'):
            error = 'Please enter the .edu email you used on Unleased.'
        elif not message:
            error = 'Please include a short message for the lister.'
        elif seeker is None:
            error = 'No Unleased account found for that email — sign up first.'
        elif seeker.pk == self.object.lister_id:
            error = "You can't send an inquiry about your own listing."
        else:
            # get_or_create respects the unique_inquiry_per_seeker_listing
            # constraint: resubmitting the form won't create duplicate rows.
            Inquiry.objects.get_or_create(
                listing=self.object,
                seeker=seeker,
                defaults={'message': message},
            )
            sent = True

        context = self.get_context_data(inquiry_error=error, inquiry_sent=sent)
        return self.render_to_response(context)


# ---------------------------------------------------------------------------
# A3 Section 2: search and ORM queries
# ---------------------------------------------------------------------------

def listing_search(request):
    """
    PUBLIC search, submitted with GET.

    The filters live in the URL (e.g. /listings/search/?q=furnished&max_rent=800),
    so the same link always loads the same results. A student can bookmark it
    or paste it in a group chat and their roommate sees the exact same list.
    Nothing here is private, so there is no reason to hide it in a POST body.
    """
    q = request.GET.get('q', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    min_bedrooms = request.GET.get('min_bedrooms', '').strip()
    lister_name = request.GET.get('lister', '').strip()
    status = request.GET.get('status', '').strip()

    results = Listing.objects.select_related('lister')

    if q:
        # Keyword search across several text fields (OR, using Q objects).
        results = results.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(building_name__icontains=q)
        )
    if max_rent.isdigit():
        results = results.filter(monthly_rent__lte=max_rent)
    if min_bedrooms.isdigit():
        results = results.filter(bedrooms__gte=min_bedrooms)
    if lister_name:
        # Relationship-spanning lookup: Listing -> lister (UnleasedUser).
        # The double underscore follows the ForeignKey into the user table.
        results = results.filter(
            Q(lister__first_name__icontains=lister_name)
            | Q(lister__last_name__icontains=lister_name)
            | Q(lister__username__icontains=lister_name)
        )
    if status in Listing.Status.values:
        results = results.filter(status=status)

    searched = any([q, max_rent, min_bedrooms, lister_name, status])

    context = {
        'results': results,
        'searched': searched,
        'total_listings': Listing.objects.count(),
        'status_choices': Listing.Status.choices,
        # Echo the inputs back so the form keeps what the user typed.
        'form_values': {
            'q': q,
            'max_rent': max_rent,
            'min_bedrooms': min_bedrooms,
            'lister': lister_name,
            'status': status,
        },
    }
    return render(request, 'listings/listing_search.html', context)


class InquiryLookupView(View):
    """
    PRIVATE search, submitted with POST: "Track my inquiries".

    A seeker types their .edu email to see the inquiries they have sent and
    whether each one was accepted. This is personal data (an email address,
    and for accepted inquiries the listing's private street address), so it
    should NOT end up in the URL, browser history, bookmarks or server logs.
    POST sends the email in the request body instead, and {% csrf_token %}
    protects the form. Refreshing or sharing the page does not replay it.
    """
    template_name = 'listings/inquiry_lookup.html'

    def get(self, request):
        # First visit: just show the empty form.
        return render(request, self.template_name, {'submitted': False})

    def post(self, request):
        email = request.POST.get('edu_email', '').strip().lower()
        error = ''
        inquiries = Inquiry.objects.none()

        if not email.endswith('.edu'):
            error = 'Please enter the .edu email you used on Unleased.'
        else:
            # Relationship-spanning lookup: Inquiry -> seeker (UnleasedUser).
            # We never show the email back in a URL; it only lives in this request.
            inquiries = (
                Inquiry.objects
                .filter(seeker__edu_email__iexact=email)
                .select_related('listing')
            )

        context = {
            'submitted': True,
            'email': email,
            'error': error,
            'inquiries': inquiries,
        }
        return render(request, self.template_name, context)


def listing_insights(request):
    """
    Insights page: summary numbers computed by the database with the ORM.

    Totals use .count() / .aggregate(), which return ONE value for the whole table.
    Grouped summaries use .values(...).annotate(Count(...)), which works like
    SQL GROUP BY and returns one row per group.
    """
    # --- Totals (one number each) ---
    totals = {
        'listings': Listing.objects.count(),
        'available': Listing.objects.filter(status=Listing.Status.AVAILABLE).count(),
        'inquiries': Inquiry.objects.count(),
        'avg_rent': Listing.objects.aggregate(avg=Avg('monthly_rent'))['avg'],
    }

    # --- Grouped summary 1: how many listings are in each status ---
    # SQL: SELECT status, COUNT(id) FROM listing GROUP BY status
    status_labels = dict(Listing.Status.choices)
    by_status = [
        {**row, 'label': status_labels.get(row['status'], row['status'])}
        for row in (
            Listing.objects
            .values('status')
            .annotate(total=Count('id'), avg_rent=Avg('monthly_rent'))
            .order_by('-total', 'status')
        )
    ]

    # --- Grouped summary 2: listings per lister (spans Listing -> lister) ---
    by_lister = (
        Listing.objects
        .values('lister__username', 'lister__first_name', 'lister__last_name')
        .annotate(total=Count('id'), avg_rent=Avg('monthly_rent'))
        .order_by('-total', 'lister__username')
    )

    # --- Grouped summary 3: which listings get the most inquiries ---
    # annotate() on the reverse relation 'inquiries' (Inquiry.listing related_name)
    most_inquired = (
        Listing.objects
        .annotate(num_inquiries=Count('inquiries'))
        .filter(num_inquiries__gt=0)
        .order_by('-num_inquiries', 'title')
    )

    context = {
        'totals': totals,
        'by_status': by_status,
        'by_lister': by_lister,
        'most_inquired': most_inquired,
    }
    return render(request, 'listings/listing_insights.html', context)


# Matches the badge colors already used for each status in static/css/base.css,
# so the chart and the rest of the UI agree on what each status "means".
STATUS_COLORS = {
    Listing.Status.AVAILABLE: '#17683A',
    Listing.Status.PENDING: '#8A5A00',
    Listing.Status.FILLED: '#9A2A18',
}


def listing_status_chart(request):
    """
    Renders a bar chart of listing counts per status as a PNG image.

    The ORM does the aggregation (one GROUP BY query); matplotlib only
    draws the numbers it's handed. The figure is written to an in-memory
    BytesIO buffer rather than a temp file on disk, and explicitly closed
    with plt.close(fig) afterwards — each request would otherwise leak
    the figure's memory for the lifetime of the server process.
    """
    status_labels = dict(Listing.Status.choices)
    counts = (
        Listing.objects
        .values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )
    # Always show all three statuses, even ones with zero listings right now.
    totals_by_status = {row['status']: row['total'] for row in counts}
    labels = [status_labels[s] for s in Listing.Status.values]
    values = [totals_by_status.get(s, 0) for s in Listing.Status.values]
    colors = [STATUS_COLORS[s] for s in Listing.Status.values]

    fig, ax = plt.subplots(figsize=(5, 3.5), dpi=120)
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, padding=3)
    ax.set_title('Listings by status')
    ax.set_xlabel('Status')
    ax.set_ylabel('Number of listings')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.yaxis.get_major_locator().set_params(integer=True)
    ax.legend(
        handles=[
            plt.Rectangle((0, 0), 1, 1, color=STATUS_COLORS[s])
            for s in Listing.Status.values
        ],
        labels=labels,
        title='Status',
        loc='upper right',
        frameon=False,
    )
    fig.tight_layout()

    buffer = BytesIO()
    fig.savefig(buffer, format='png')
    plt.close(fig)  # free the figure's memory now that it's in `buffer`
    buffer.seek(0)
    return HttpResponse(buffer.getvalue(), content_type='image/png')


# ---------------------------------------------------------------------------
# A3 Section 6: JSON APIs
# ---------------------------------------------------------------------------

def _filter_listings(request):
    """Shared query-param filtering, reused by the API and its plain-text twin."""
    q = request.GET.get('q', '').strip()
    max_rent = request.GET.get('max_rent', '').strip()
    min_bedrooms = request.GET.get('min_bedrooms', '').strip()
    status = request.GET.get('status', '').strip()

    results = Listing.objects.select_related('lister')
    if q:
        results = results.filter(
            Q(title__icontains=q)
            | Q(description__icontains=q)
            | Q(building_name__icontains=q)
        )
    if max_rent.isdigit():
        results = results.filter(monthly_rent__lte=max_rent)
    if min_bedrooms.isdigit():
        results = results.filter(bedrooms__gte=min_bedrooms)
    if status in Listing.Status.values:
        results = results.filter(status=status)
    return results


def listing_api(request):
    """
    Public JSON API (FBV): GET /listings/api/?q=...&max_rent=...&status=...

    Same filters as listing_search(), but instead of rendering HTML for a
    person, it returns machine-readable JSON for another program to consume.
    JsonResponse serializes the dict to JSON and sets
    Content-Type: application/json automatically.
    """
    results = _filter_listings(request)
    data = {
        'count': results.count(),
        'results': [
            {
                'id': listing.id,
                'title': listing.title,
                'monthly_rent': str(listing.monthly_rent),
                'bedrooms': listing.bedrooms,
                'bathrooms': str(listing.bathrooms),
                'status': listing.status,
                'lister': listing.lister.username,
                'url': listing.get_absolute_url(),
            }
            for listing in results
        ],
    }
    return JsonResponse(data)


def listing_api_text(request):
    """
    Same data and same query-param filters as listing_api(), but returned
    with a plain HttpResponse as tab-separated text instead of JSON.

    Compare this response's Content-Type header (text/plain) against
    listing_api()'s (application/json) — same underlying queryset, two very
    different responses depending on which HttpResponse subclass builds it.
    """
    results = _filter_listings(request)
    lines = [
        f"{listing.id}\t{listing.title}\t${listing.monthly_rent}/mo\t{listing.status}"
        for listing in results
    ]
    return HttpResponse('\n'.join(lines) or 'No listings match.', content_type='text/plain')


def listing_api_by_status(request):
    """
    Chart-ready JSON (FBV): GET /listings/api/by-status/

    Same GROUP BY as the Insights page's "by status" table, but returned as
    a flat JSON array (not wrapped in a {"results": [...]} envelope) so it
    can be pointed at directly from a Vega-Lite spec's data.url. Always
    includes all three statuses, even ones with zero listings right now, so
    the bar chart doesn't silently drop a category.
    """
    status_labels = dict(Listing.Status.choices)
    counts = (
        Listing.objects
        .values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )
    totals_by_status = {row['status']: row['total'] for row in counts}
    data = [
        {'status': status_labels[s], 'total': totals_by_status.get(s, 0)}
        for s in Listing.Status.values
    ]
    return JsonResponse(data, safe=False)


def vega_charts(request):
    """Page embedding the two Vega-Lite charts, each reading a listings:api* endpoint directly."""
    return render(request, 'listings/vega_charts.html')


# ---------------------------------------------------------------------------
# A4 Part 1: dedicated chart endpoints (/vega-lite/chart1.png, chart1.json, ...)
# ---------------------------------------------------------------------------

# The .vl.json files in docs/vega-lite/ (built in the Vega-Lite editor) are the
# single source of truth for both charts. Each entry names the internal API the
# chart reads from: the route (for data.url) and the view function behind it.
VEGA_SPEC_DIR = settings.BASE_DIR / 'docs' / 'vega-lite'
VEGA_CHARTS = {
    'chart1': {
        'file': 'chart1-bar-by-status.vl.json',
        'api_route': 'listings:api_by_status',
        'api_view': listing_api_by_status,
    },
    'chart2': {
        'file': 'chart2-scatter-rent-vs-bedrooms.vl.json',
        'api_route': 'listings:api',
        'api_view': listing_api,
    },
}


def _vega_spec(request, chart):
    """Load a chart's spec and point data.url at THIS server's internal API."""
    config = VEGA_CHARTS.get(chart)
    if config is None:
        raise Http404(f'No chart named {chart!r}.')
    spec = json.loads((VEGA_SPEC_DIR / config['file']).read_text())
    spec['data']['url'] = request.build_absolute_uri(reverse(config['api_route']))
    return spec, config


def vega_chart_spec(request, chart):
    """
    GET /vega-lite/<chart>.json: the chart's Vega-Lite spec.

    data.url is the absolute URL of the internal API on whichever host serves
    this (localhost or PythonAnywhere), so this link can be pasted straight
    into the online Vega-Lite editor and the chart loads live data.
    """
    spec, _ = _vega_spec(request, chart)
    return JsonResponse(spec, json_dumps_params={'indent': 2})


def vega_chart_png(request, chart):
    """
    GET /vega-lite/<chart>.png: the same Vega-Lite chart rendered to a PNG on
    the server (with vl-convert), returned with HttpResponse as image/png.

    The browser-embedded charts let the browser fetch data.url. A server-side
    render can't make an HTTP request back to its own site (PythonAnywhere's
    free tier blocks that), so instead we call the very same internal API view
    the URL points to and hand its JSON rows to the renderer for this one
    request. Nothing is stored; the spec files themselves still use data.url.
    The PNG is built in memory and sent as bytes, never written to disk.
    """
    spec, config = _vega_spec(request, chart)
    api_payload = json.loads(config['api_view'](request).content)

    data_format = spec['data'].get('format', {})
    rows = api_payload[data_format['property']] if 'property' in data_format else api_payload
    spec['data'] = {'values': rows}
    if 'parse' in data_format:
        spec['data']['format'] = {'parse': data_format['parse']}

    png_bytes = vl_convert.vegalite_to_png(spec, scale=2)
    return HttpResponse(png_bytes, content_type='image/png')


# ---------------------------------------------------------------------------
# A4 Part 2: external API integration (keyless) + triangulation
# ---------------------------------------------------------------------------

# UIUC's Alma Mater statue — used as the fixed "campus center" reference point.
CAMPUS_LAT = 40.1020
CAMPUS_LON = -88.2272

# Nominatim (OpenStreetMap) requires a descriptive User-Agent identifying the
# app, not a browser string, as a condition of its free/keyless usage policy.
GEOCODER_USER_AGENT = 'Unleased-DjangoCourseProject/1.0 (+https://github.com/SurutheJ/2_Unleased)'


def _haversine_miles(lat1, lon1, lat2, lon2):
    """Great-circle distance between two lat/lon points, in miles."""
    earth_radius_miles = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return earth_radius_miles * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def listing_proximity(request):
    """
    PUBLIC JSON API (FBV): GET /listings/api/proximity/?listing_id=<pk>

    Pulls one Listing from our own database (internal data), geocodes its
    street address through Nominatim — a keyless public API — and returns
    how far that listing is from the UIUC campus. The external geocode
    (lat/lon) is only ever held in this request's local variables; it is
    never written to the database, so re-running this view always makes a
    fresh external call rather than reading a stale, stored result.

    The street address itself is private (same rule as everywhere else in
    this app — see listing_search()/InquiryLookupView): it is sent to the
    geocoder server-side to compute a distance, but it is never echoed back
    in the JSON response.
    """
    listing_id = request.GET.get('listing_id', '').strip()
    if not listing_id.isdigit():
        return JsonResponse({'error': 'Provide an existing listing via ?listing_id=<id>.'}, status=400)

    listing = get_object_or_404(Listing, pk=listing_id)
    full_address = f"{listing.street_address}, {listing.city}, {listing.state} {listing.zip_code}"

    try:
        geocode_response = requests.get(
            'https://nominatim.openstreetmap.org/search',
            params={'q': full_address, 'format': 'json', 'limit': 1},
            headers={'User-Agent': GEOCODER_USER_AGENT},
            timeout=5,
        )
        geocode_response.raise_for_status()
    except requests.RequestException as exc:
        return JsonResponse({'error': f'Could not reach the geocoding service: {exc}'}, status=502)

    geocode_results = geocode_response.json()
    if not geocode_results:
        return JsonResponse({'error': 'That listing\'s address could not be geocoded.'}, status=404)

    listing_lat = float(geocode_results[0]['lat'])
    listing_lon = float(geocode_results[0]['lon'])
    distance_miles = _haversine_miles(CAMPUS_LAT, CAMPUS_LON, listing_lat, listing_lon)

    return JsonResponse({
        'listing_id': listing.id,
        'title': listing.title,
        'building_name': listing.building_name,
        'monthly_rent': str(listing.monthly_rent),
        'distance_from_campus_miles': round(distance_miles, 2),
        'geocoder': 'nominatim.openstreetmap.org',
    })


def listing_proximity_page(request):
    """HTML page: pick a listing, fetch listing_proximity() client-side, show the result."""
    context = {'listings': Listing.objects.select_related('lister')}
    return render(request, 'listings/listing_proximity.html', context)


# ---------------------------------------------------------------------------
# Part 3: CSV / JSON export + reports page
# ---------------------------------------------------------------------------

# Exports are public downloads, so street_address, lease_document and
# raw_whatsapp_text are deliberately left out (same privacy rule as the
# rest of the app: the address is only revealed after an accepted inquiry).
EXPORT_FIELDS = [
    'id', 'title', 'building_name', 'city', 'state', 'zip_code',
    'monthly_rent', 'utilities_included', 'bedrooms', 'bathrooms',
    'is_furnished', 'status', 'available_from', 'available_until',
    'lister', 'is_property_verified',
]


def _export_rows():
    """Listings ordered by id, as plain dicts of strings/bools/ints (shared by CSV and JSON)."""
    listings = Listing.objects.select_related('lister').order_by('id')
    return [
        {
            'id': l.id,
            'title': l.title,
            'building_name': l.building_name,
            'city': l.city,
            'state': l.state,
            'zip_code': l.zip_code,
            'monthly_rent': str(l.monthly_rent),
            'utilities_included': l.utilities_included,
            'bedrooms': l.bedrooms,
            'bathrooms': str(l.bathrooms),
            'is_furnished': l.is_furnished,
            'status': l.status,
            'available_from': l.available_from.isoformat(),
            'available_until': l.available_until.isoformat(),
            'lister': l.lister.username,
            'is_property_verified': l.is_property_verified,
        }
        for l in listings
    ]


def _export_filename(extension):
    """listings_YYYY-MM-DD_HH-MM.<ext>, in the project's local time zone."""
    return f"listings_{timezone.localtime():%Y-%m-%d_%H-%M}.{extension}"


def export_listings_csv(request):
    """Download every listing as CSV: header row first, then one row per listing."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{_export_filename("csv")}"'
    writer = csv.DictWriter(response, fieldnames=EXPORT_FIELDS)
    writer.writeheader()
    writer.writerows(_export_rows())
    return response


def export_listings_json(request):
    """Download every listing as pretty-printed JSON with generated_at / record_count metadata."""
    rows = _export_rows()
    response = JsonResponse(
        {
            'generated_at': timezone.now().isoformat(),
            'record_count': len(rows),
            'listings': rows,
        },
        json_dumps_params={'indent': 2},
    )
    response['Content-Disposition'] = f'attachment; filename="{_export_filename("json")}"'
    return response


def listing_reports(request):
    """
    Reports page: totals line, two grouped summaries, and the export buttons.

    Both grouped summaries use conditional aggregation so "active vs all"
    comes from one query: Count('id') is every row in the group, and
    Count('id', filter=Q(...)) only counts rows matching the condition.
    """
    status_labels = dict(Listing.Status.choices)
    totals = {
        'listings': Listing.objects.count(),
        'inquiries': Inquiry.objects.count(),
        'listers': UnleasedUser.objects.filter(listings__isnull=False).distinct().count(),
        'avg_rent': Listing.objects.aggregate(avg=Avg('monthly_rent'))['avg'],
    }

    # Summary 1: listings per status (SQL GROUP BY), with average rent.
    by_status = [
        {**row, 'label': status_labels.get(row['status'], row['status'])}
        for row in (
            Listing.objects
            .values('status')
            .annotate(total=Count('id'), avg_rent=Avg('monthly_rent'))
            .order_by('-total', 'status')
        )
    ]

    # Summary 2: inquiries per listing, "active" (pending/accepted) vs all.
    inquiries_per_listing = (
        Listing.objects
        .annotate(
            all_inquiries=Count('inquiries'),
            active_inquiries=Count(
                'inquiries',
                filter=~Q(inquiries__status=Inquiry.Status.DECLINED),
            ),
        )
        .order_by('-all_inquiries', 'title')
    )

    context = {
        'totals': totals,
        'by_status': by_status,
        'inquiries_per_listing': inquiries_per_listing,
    }
    return render(request, 'listings/reports.html', context)
