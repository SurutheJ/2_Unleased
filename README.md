# 2_Unleased

**Unleased** is a Django web app for UIUC students to post, find, and manage
sublease listings — a structured, verified alternative to the informal
WhatsApp group chats students currently use. It adds `.edu` verification,
roommate-compatibility fields, formal inquiries/visit scheduling, and a
post-sublease review system as a trust layer WhatsApp threads don't have.

## Project structure

```
2_Unleased/
├── accounts/                  # Custom user model, verification, reviews
├── listings/                  # Listings, visit slots, inquiries, saved listings
├── unleased_project/
│   ├── settings/
│   │   ├── base.py            # Settings shared by every environment
│   │   ├── dev.py              # DEBUG=True, local-friendly ALLOWED_HOSTS
│   │   └── prod.py             # DEBUG=False, hardened, requires ALLOWED_HOSTS
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── templates/                  # Project-wide templates: base.html + partials (navbar, footer)
├── static/
│   └── css/base.css            # Site-wide stylesheet, linked from templates/base.html
├── docs/
│   ├── wireframes/             # UI wireframes/mockups
│   ├── screenshots/            # Browser-output screenshots (Sections 2 & 3)
│   ├── vega-lite/              # Submitted Vega-Lite chart specs (A4 Part 1)
│   ├── branching-strategy/     # How we use git branches as a team
│   └── notes/notes.txt         # Weekly progress log (updated every week)
├── manage.py
├── seed_data.py                 # Populates the DB with realistic fake data
├── requirements.txt
├── .env.example                 # Template for required environment variables
└── .gitignore
```

## Setup (first time)

1. Clone the repo and `cd` into it.
2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate      # Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Copy the environment template and fill in real values:
   ```
   cp .env.example .env
   ```
   At minimum, generate a real `SECRET_KEY`:
   ```
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```
   and paste it into `.env`. **Never commit `.env`** — it's gitignored on purpose.
5. Run migrations:
   ```
   python manage.py migrate
   ```
6. Load the sample data. **Do this before opening the site**: the database
   file (`db.sqlite3`) is not stored in Git, so a fresh clone starts empty and
   the listing pages will show the "No listings yet" message until you seed it.
   ```
   python seed_data.py
   ```
   (Optional) To log into `/admin/` with your own account, also run
   `python manage.py createsuperuser`.
7. Run the dev server:
   ```
   python manage.py runserver
   ```
   This uses `unleased_project.settings.dev` by default (see `manage.py`).

## Running in production mode

Production settings (`unleased_project.settings.prod`) turn `DEBUG` off,
require `ALLOWED_HOSTS` to be set explicitly, and enable HTTPS/cookie
hardening. Point `DJANGO_SETTINGS_MODULE` at it via a real host
environment variable (not `.env`):

```
DJANGO_SETTINGS_MODULE=unleased_project.settings.prod \
ALLOWED_HOSTS=your-domain.com \
python manage.py check --deploy
```

## Static files and deployment (PythonAnywhere)

- **Static files:** our CSS lives in `static/css/base.css` (`STATICFILES_DIRS`).
  `base.html` loads it with `{% load static %}` and `{% static 'css/base.css' %}`,
  so every page that extends `base.html` is styled. `collectstatic` copies it,
  plus the admin assets, into `staticfiles/` (`STATIC_ROOT`). That folder is
  gitignored and is rebuilt on the server.
- **Production check locally:**
  ```
  export DJANGO_SETTINGS_MODULE=unleased_project.settings.prod ALLOWED_HOSTS=127.0.0.1 SECURE_SSL_REDIRECT=False
  python manage.py collectstatic --noinput
  python manage.py runserver --insecure
  ```
  (`--insecure` lets runserver serve the collected files with `DEBUG=False`;
  on PythonAnywhere the web tab's static mapping serves them instead.)
- **Database:** `db.sqlite3` was committed only for the A4 initial deploy. Since
  A5 it is gitignored again, because the production copy now holds real user
  accounts that a `git pull` must never overwrite. Each machine keeps its own
  database (`python manage.py migrate` + `python seed_data.py` locally). We will
  move to Postgres afterwards.
- **Python:** use Python 3.13 (or 3.11+) for the virtualenv; `matplotlib==3.11.0`
  in `requirements.txt` does not support older versions.
- **Route check:** `python manage.py test listings` loads every page and API
  route, and checks which ones are public and which require login.
- **Live site:** https://parulmudaliar.pythonanywhere.com (PythonAnywhere user
  `ParulMudaliar`, teacher access given to `mohitg27`).

## Environment variables

See `.env.example` for the full list. Summary:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django's cryptographic signing key — must be unique and secret per deployment |
| `DEBUG` | `True` locally, always `False` in production (enforced in `settings/prod.py`) |
| `ALLOWED_HOSTS` | Comma-separated list of hostnames Django will serve |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load (`unleased_project.settings.dev` or `.prod`) |
| `MAPS_API_KEY` | Placeholder third-party API key, read the same way real secrets will be |

## Authentication (A5 Part 1)

Login uses [django-allauth](https://docs.allauth.org/) with custom templates
in `templates/account/` styled like the rest of the site:

| Page | URL | Notes |
|---|---|---|
| Log in | `/accounts/login/` | Username **or** email + password, "Remember me" |
| Sign up | `/accounts/signup/` | Email, username, password (Django's password rules apply) |
| Log out | `/accounts/logout/` | A POST form with CSRF; visiting the URL alone does not log you out |

Settings (`unleased_project/settings/base.py`): `LOGIN_URL = 'account_login'`,
`LOGIN_REDIRECT_URL = 'home'`, `LOGOUT_REDIRECT_URL = 'home'`. A logged-out
visitor who opens a protected page is sent to the login page and brought back
to that page afterwards (`?next=`).

Anyone can sign up, but `.edu` emails are marked as verified students:
`accounts/signals.py` copies the signup email into `UnleasedUser.edu_email` and
sets `is_edu_verified=True` for `.edu` addresses.

**What needs login**

| Public (no login) | Login required |
|---|---|
| Home, Browse, Available now, Search, listing detail pages | My inquiries, sending an inquiry, Insights (+ its chart image), Charts, Nearby campus, Reports, CSV/JSON exports |
| **`/listings/api/by-status/`**, the one public API | `/listings/api/`, `/listings/api.txt`, `/listings/api/proximity/` (return **401 JSON** when logged out) |
| `/vega-lite/chart1.png` / `.json` (built on the public API) | `/vega-lite/chart2.png` / `.json` (built on a protected API) |

Pages use `@login_required` / `LoginRequiredMixin`; APIs use an
`@api_login_required` decorator (`listings/views.py`) so scripts get a JSON
error instead of an HTML login page. The navbar only shows the protected tabs
once you are logged in, and shows Log in / Sign up or Hi, *name* / Log out.

## Navigation and URLs

The home page (`/`) shows the newest available sublease listings, and the
navbar links to **Home**, **Browse** (`/listings/`) and **Available now**
(`/listings/cbv-base/`), all built with `{% url %}` route names. Every listing
card links to its own detail page at `/listings/<pk>/` through
`Listing.get_absolute_url()`, so templates never hand-build listing URLs.

## UI styling

Page styling lives in one place, `static/css/base.css`, linked from
`templates/base.html` with `{% load static %}` — not inlined per-template.
It sets the color palette, layout/spacing, the `Poppins` display font used
for the logo and headings, and a subtle gradient header band. In production
(`settings/prod.py`), `ManifestStaticFilesStorage` renames each static file
with a content hash on `collectstatic` (e.g. `base.css` → `base.<hash>.css`)
so browsers can cache static files indefinitely without ever serving a
stale one after a deploy.

## Search and insights

**Search** (`/listings/search/`) is a public GET form that filters listings by
keyword, max rent, min bedrooms, status and lister name; the filters live in the
URL, so a search link can be bookmarked or shared and always loads the same
results. **My inquiries** (`/listings/my-inquiries/`) shows the status of the
inquiries you sent, and the private address of any accepted listing. (In A3 it
was a POST form where you typed a `.edu` email; since A5 it requires login and
only ever shows `request.user`'s own inquiries.) **Insights** (`/listings/insights/`) shows
ORM aggregations: totals (`count()`, `Avg`) and grouped summaries
(`values().annotate(Count())`) by status, by lister, and by number of inquiries.
It also embeds a server-rendered bar chart (`/listings/insights/chart.png`) of
listing counts by status, generated with Matplotlib from that same
status-grouped query — see "Data visualization" below.

## Forms & user input

Two forms demonstrate the GET/POST split, and one CBV handles both verbs on
the same URL:

- **GET form — search** (`/listings/search/`, already covered under
  "Search and insights" above): filters live in the URL as query params, so
  the page never modifies data and results are shareable/bookmarkable.
- **POST form — send an inquiry** (`/listings/<pk>/`, `listings:detail`):
  the listing detail page includes an "Inquire about this listing" form
  (a message; since A5 the sender is the logged-in user, and logged-out
  visitors see a "Log in to send an inquiry" button instead). Submitting it **creates** an `Inquiry` row —
  real data modification — so it uses `method="post"` and
  `{% csrf_token %}`, never GET query params. Django rejects the POST with
  403 if the token is missing or invalid.
- **CBV handling both GET and POST**: `ListingDetailView` (`listings/views.py`)
  is a generic `DetailView` with an added `post()` method. `GET` renders the
  listing as usual; `POST` requires login, validates the message, uses
  `request.user` as the seeker, and calls `Inquiry.objects.get_or_create(...)`
  (which also respects the `unique_inquiry_per_seeker_listing` constraint,
  so resubmitting the form can't create a duplicate inquiry).

## Creating APIs

Two endpoints in `listings/views.py` serve the same filtered `Listing` data,
but through different `HttpResponse` subclasses — useful for comparing them
directly:

| Endpoint | URL name | Response type | Content-Type |
|---|---|---|---|
| `listing_api` | `listings:api` (`/listings/api/`) | `JsonResponse` | `application/json` |
| `listing_api_text` | `listings:api_text` (`/listings/api.txt`) | `HttpResponse` | `text/plain` |

Both are function-based views and accept the same query-param filters as
`listing_search()` — `q`, `max_rent`, `min_bedrooms`, `status` — e.g.
`/listings/api/?max_rent=800&status=available`. `listing_api()` builds a
plain Python dict (`count` + a list of listing fields) and hands it to
`JsonResponse`, which serializes it to JSON and sets the response header
automatically. `listing_api_text()` runs the identical filtered queryset
through `_filter_listings()` but formats it as tab-separated plain text
inside a manually-constructed `HttpResponse`. Opening both URLs side by side
shows the same underlying data, but the browser renders one as raw text and
lets tools like `curl -i` show the different `Content-Type` headers.

## Internal JSON API & Vega-Lite charts

Two of the "Creating APIs" endpoints double as data sources for client-side
charts, so they're chart-ready (flat JSON arrays or a `results` list) rather
than built around an HTML response:

| Endpoint | URL name | Returns |
|---|---|---|
| `listing_api` | `listings:api` (`/listings/api/`) | `{"count": N, "results": [...]}` — one row per listing |
| `listing_api_by_status` | `listings:api_by_status` (`/listings/api/by-status/`) | `[{"status": ..., "total": ...}, ...]` — always all 3 statuses, even at 0 |

**Charts page** (`/listings/charts/`, `listings:vega_charts`) embeds two
[Vega-Lite](https://vega.github.io/vega-lite/) charts via `vega-embed`
(loaded from a CDN), each pointed at one of the endpoints above through
`data.url` — neither spec uses inline data:

- **Bar chart**: listings grouped by status, from `listing_api_by_status`.
- **Scatter chart**: monthly rent vs. bedroom count across every listing,
  from `listing_api`'s `results` array (`format: {property: "results"}`).
  `monthly_rent` is serialized as a string in the JSON (to keep `Decimal`
  precision), so the spec adds `format.parse: {"monthly_rent": "number"}` —
  without it, Vega-Lite would plot it as a categorical field.

The two specs are also submitted standalone in
[`docs/vega-lite/`](docs/vega-lite/) (`chart1-bar-by-status.vl.json`,
`chart2-scatter-rent-vs-bedrooms.vl.json`), with absolute `data.url`s for
grading outside this app; the versions embedded in `vega_charts.html` use
`{% url %}`-generated relative URLs so the page works on any host.

**Dedicated chart endpoints** (project-level routes in `unleased_project/urls.py`):

| URL | Returns |
|---|---|
| `/vega-lite/chart1.png` | Bar chart (listings by status) as a PNG image (`image/png`) |
| `/vega-lite/chart2.png` | Scatter chart (rent vs. bedrooms) as a PNG image |
| `/vega-lite/chart1.json` | The bar chart's Vega-Lite spec, with `data.url` set to this server's API |
| `/vega-lite/chart2.json` | The scatter chart's Vega-Lite spec |

The `.json` endpoints serve the specs from `docs/vega-lite/` with an absolute
`data.url` for whichever host you're on, so
`https://parulmudaliar.pythonanywhere.com/vega-lite/chart1.json` can be opened
directly in the online Vega-Lite editor. The `.png` endpoints render the same
specs on the server with `vl-convert-python`: the view calls the same internal
API view that `data.url` points to and renders its rows in memory (nothing is
stored), because PythonAnywhere's free tier does not let the server make HTTP
requests back to itself. The Charts page shows both the live embedded charts
and these PNG versions, with alt text and captions.

The public read-only APIs (`/listings/api/`, `/listings/api.txt`,
`/listings/api/by-status/`, `/listings/api/proximity/`) and the spec endpoints
send `Access-Control-Allow-Origin: *`, so other sites, like the online
Vega-Lite editor, are allowed to load them.

## External API integration: distance from campus

**`listing_proximity`** (`listings:api_proximity`,
`/listings/api/proximity/?listing_id=<pk>`) is a keyless external API
integration: given one of our own `Listing` rows (internal data), it
geocodes that listing's private street address through
[Nominatim](https://nominatim.openstreetmap.org/) (OpenStreetMap's free,
keyless geocoder) and returns the great-circle distance from that address to
the UIUC Alma Mater statue, computed with the Haversine formula.

- Calls `requests.get(..., params=..., timeout=5)` then
  `.raise_for_status()`; `requests.RequestException` is caught and turned
  into a `502` JSON error instead of a stack trace, so a geocoder outage or
  timeout fails cleanly.
- The external result (the geocoded lat/lon) is only ever held in local
  Python variables for the duration of one request — it is **never written
  to the database** — so every call re-geocodes from scratch instead of
  trusting a stored value that could go stale if the address changes.
- The street address itself follows the same privacy rule as the rest of
  the app (see "Search and insights" above): it's sent to Nominatim
  server-side to compute a distance, but it is never included in the JSON
  response that reaches the browser.

**`/listings/proximity/`** (`listings:proximity`) is a small HTML page with
a listing picker; clicking "Check distance" calls `api_proximity` with
`fetch()` client-side and renders the resulting mileage — a visual way to
exercise the API without `curl`.

## CSV & JSON exports and reports

**Reports page** (`/listings/reports/`, `listings:reports`) shows a totals
line (total listings, inquiries, listers and average rent), two grouped
summaries (listings by status with average rent, and inquiries per listing,
active vs. all) in tables with headers and `{% empty %}` rows, and visible
**Download CSV** and **Download JSON** buttons.

| Export | URL | Details |
|---|---|---|
| CSV | `/listings/export/listings.csv` | `text/csv`, header row first, listings ordered by id, file named `listings_YYYY-MM-DD_HH-MM.csv` |
| JSON | `/listings/export/listings.json` | Pretty-printed (`indent=2`) with `generated_at` (ISO timestamp), `record_count` and `listings: [...]`, file named `listings_YYYY-MM-DD_HH-MM.json` |

Private fields (street address, lease document, raw WhatsApp text) are left out
of both exports.

## Data visualization

`/listings/insights/chart.png` (`listings:insights_chart`) is a Django view
that aggregates `Listing` counts per status with the ORM, draws a Matplotlib
bar chart (title, axis labels, and a legend mapping each bar's color to its
status), and returns it as a PNG `HttpResponse`. The figure is drawn into an
in-memory `BytesIO` buffer instead of a temp file, and the Matplotlib figure
is explicitly closed with `plt.close(fig)` right after — otherwise every
request to the page would leak that figure's memory for the life of the
server process. The `<img>` tag on the Insights page points straight at this
URL, so the chart always reflects the current database.

## Screenshots

### Section 2 — Four Django views

Browser output for each of the four required view types, confirming all
four work and are wired up behind named URLs.

| View | URL name | Screenshot |
|---|---|---|
| `HttpResponse` + `loader.get_template()` FBV | `listings:manual` | [section2-01-httpresponse-fbv.jpg](docs/screenshots/section2-01-httpresponse-fbv.jpg) |
| `render()` FBV | `listings:render` | [section2-02-render-fbv.jpg](docs/screenshots/section2-02-render-fbv.jpg) |
| Base `View` CBV | `listings:cbv_base` | [section2-03-base-cbv.jpg](docs/screenshots/section2-03-base-cbv.jpg) |
| Generic `ListView` CBV | `listings:cbv_generic` | [section2-04-generic-cbv.jpg](docs/screenshots/section2-04-generic-cbv.jpg) |

### Section 3 — Reusable templates

The same four views rendered through the shared, inheriting template
(`templates/base.html` + `listings/listing_list.html`), plus the listing
detail page and the `{% for %}...{% empty %}` empty-state case.

| View | URL name | Screenshot |
|---|---|---|
| `HttpResponse` FBV | `listings:manual` | [01-httpresponse-fbv-list.png](docs/screenshots/01-httpresponse-fbv-list.png) |
| `render()` FBV | `listings:render` | [02-render-fbv-list.png](docs/screenshots/02-render-fbv-list.png) |
| Base CBV | `listings:cbv_base` | [03-base-cbv-list.png](docs/screenshots/03-base-cbv-list.png) |
| Generic CBV | `listings:cbv_generic` | [04-generic-cbv-list.png](docs/screenshots/04-generic-cbv-list.png) |
| Listing detail page (shared template) | `listings:detail` | [05-listing-detail.png](docs/screenshots/05-listing-detail.png) |
| Empty state (`{% empty %}` block, no listings in DB) | `listings:cbv_generic` | [06-empty-state.png](docs/screenshots/06-empty-state.png) |

### A3 Section 1: URL linking and navigation

| What it shows | URL | Screenshot |
|---|---|---|
| Home page | `/` (`home`) | [a3-s1-01-home.png](docs/screenshots/a3-s1-01-home.png) |
| Navigation working (active tab underlined) | `/listings/` (`listings:list`) | [a3-s1-02-navigation.png](docs/screenshots/a3-s1-02-navigation.png) |
| Detail page opened by clicking a card | `/listings/<pk>/` (`listings:detail`) | [a3-s1-03-detail.png](docs/screenshots/a3-s1-03-detail.png) |

### A3 Section 2: ORM queries and data presentation

| What it shows | URL | Screenshot |
|---|---|---|
| GET search with filters visible in the URL | `/listings/search/?max_rent=800` | [a3-s2-01-get-search.png](docs/screenshots/a3-s2-01-get-search.png) |
| POST inquiry lookup results (URL has no email) | `/listings/my-inquiries/` | [a3-s2-02-post-lookup.png](docs/screenshots/a3-s2-02-post-lookup.png) |
| Aggregation summaries | `/listings/insights/` | [a3-s2-03-insights.png](docs/screenshots/a3-s2-03-insights.png) |
| `{% empty %}` state for a search with no matches | `/listings/search/?q=zzz` | [a3-s2-04-empty-search.png](docs/screenshots/a3-s2-04-empty-search.png) |

### Section 3: Static files & UI styling

| What it shows | URL | Screenshot |
|---|---|---|
| Home page with `static/css/base.css` applied (Poppins logo, gradient nav) | `/` | [section3-01-home-styled.png](docs/screenshots/section3-01-home-styled.png) |
| Insights page with the same stylesheet, including the chart panel | `/listings/insights/` | [section3-02-insights-styled.png](docs/screenshots/section3-02-insights-styled.png) |

### Section 4: Data visualization (Matplotlib)

| What it shows | URL | Screenshot |
|---|---|---|
| Bar chart of listings by status (title, axis labels, legend) served as a PNG | `/listings/insights/chart.png` | [section4-01-status-chart.png](docs/screenshots/section4-01-status-chart.png) |

### A3 Section 5: Forms & User Input

| What it shows | URL | Screenshot |
|---|---|---|
| GET search form with filters in the URL (see also Section 2 above) | `/listings/search/?max_rent=800` | [a3-s2-01-get-search.png](docs/screenshots/a3-s2-01-get-search.png) |
| POST inquiry form on the listing detail page, with `{% csrf_token %}` visible in page source | `/listings/<pk>/` | [a3-s5-01-inquiry-form.png](docs/screenshots/a3-s5-01-inquiry-form.png) |
| Successful POST: "Your inquiry was sent!" confirmation from the same CBV | `/listings/<pk>/` | [a3-s5-02-inquiry-sent.png](docs/screenshots/a3-s5-02-inquiry-sent.png) |

### A3 Section 6: Creating APIs

| What it shows | URL | Screenshot |
|---|---|---|
| Raw JSON response (`Content-Type: application/json`) | `/listings/api/?max_rent=800` | [a3-s6-01-json-api.png](docs/screenshots/a3-s6-01-json-api.png) |
| Same filtered data as plain text (`Content-Type: text/plain`) | `/listings/api.txt?max_rent=800` | [a3-s6-02-api-text.png](docs/screenshots/a3-s6-02-api-text.png) |

### A4 Part 1: Internal API & Vega-Lite charts

| What it shows | URL | Screenshot |
|---|---|---|
| Chart-ready bar-chart JSON (always all 3 statuses) | `/listings/api/by-status/` | [a4-p1-01-by-status-json.png](docs/screenshots/a4-p1-01-by-status-json.png) |
| Both Vega-Lite charts rendered on the Charts page | `/listings/charts/` | [a4-p1-02-vega-charts.png](docs/screenshots/a4-p1-02-vega-charts.png) |
| Bar chart served as a PNG | `/vega-lite/chart1.png` | [a4-p1-03-chart1-png.png](docs/screenshots/a4-p1-03-chart1-png.png) |
| Scatter chart served as a PNG | `/vega-lite/chart2.png` | [a4-p1-04-chart2-png.png](docs/screenshots/a4-p1-04-chart2-png.png) |
| Spec opened in the online Vega-Lite editor via the deployed API | `/vega-lite/chart1.json` | [a4-p1-05-vega-editor.png](docs/screenshots/a4-p1-05-vega-editor.png) |

### A4 Part 2: External API integration

| What it shows | URL | Screenshot |
|---|---|---|
| `listing_proximity` JSON: internal listing + externally-geocoded distance | `/listings/api/proximity/?listing_id=5` | [a4-p2-01-proximity-json.png](docs/screenshots/a4-p2-01-proximity-json.png) |
| Error handling: invalid/missing `listing_id` | `/listings/api/proximity/?listing_id=abc` | [a4-p2-02-proximity-error.png](docs/screenshots/a4-p2-02-proximity-error.png) |
| HTML page calling the API client-side with `fetch()` | `/listings/proximity/` | [a4-p2-03-proximity-page.png](docs/screenshots/a4-p2-03-proximity-page.png) |

### A4 Part 3: CSV & JSON exports and reports

| What it shows | URL | Screenshot |
|---|---|---|
| Reports page: totals, two grouped summaries, download buttons | `/listings/reports/` | [a4-p3-01-reports.png](docs/screenshots/a4-p3-01-reports.png) |
| Downloaded CSV opened (header row + ordered rows) | `/listings/export/listings.csv` | [a4-p3-02-csv-export.png](docs/screenshots/a4-p3-02-csv-export.png) |
| Downloaded JSON (metadata + listings) | `/listings/export/listings.json` | [a4-p3-03-json-export.png](docs/screenshots/a4-p3-03-json-export.png) |

### A4 Part 4: Deployment (PythonAnywhere)

| What it shows | URL | Screenshot |
|---|---|---|
| Styled home page on the deployed site | `https://parulmudaliar.pythonanywhere.com/` | [a4-p4-01-deployed-home.png](docs/screenshots/a4-p4-01-deployed-home.png) |
| Internal API on the deployed site | `/listings/api/by-status/` | [a4-p4-02-deployed-api.png](docs/screenshots/a4-p4-02-deployed-api.png) |
| Vega-Lite charts on the deployed site | `/listings/charts/` | [a4-p4-03-deployed-charts.png](docs/screenshots/a4-p4-03-deployed-charts.png) |

## Branching strategy

See [`docs/branching-strategy/`](docs/branching-strategy/) for the full
write-up. Short version: `main` is always deployable; work happens on
short-lived `feature/*` branches and gets merged back via PR.

