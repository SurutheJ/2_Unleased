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

## Environment variables

See `.env.example` for the full list. Summary:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django's cryptographic signing key — must be unique and secret per deployment |
| `DEBUG` | `True` locally, always `False` in production (enforced in `settings/prod.py`) |
| `ALLOWED_HOSTS` | Comma-separated list of hostnames Django will serve |
| `DJANGO_SETTINGS_MODULE` | Which settings module to load (`unleased_project.settings.dev` or `.prod`) |
| `MAPS_API_KEY` | Placeholder third-party API key, read the same way real secrets will be |

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
results. **My inquiries** (`/listings/my-inquiries/`) is a POST form where a
seeker enters their `.edu` email to see the status of inquiries they sent, and
the private address of any accepted listing; it uses POST and `{% csrf_token %}`
so the email never appears in the URL. **Insights** (`/listings/insights/`) shows
ORM aggregations: totals (`count()`, `Avg`) and grouped summaries
(`values().annotate(Count())`) by status, by lister, and by number of inquiries.
It also embeds a server-rendered bar chart (`/listings/insights/chart.png`) of
listing counts by status, generated with Matplotlib from that same
status-grouped query — see "Data visualization" below.

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

## Branching strategy

See [`docs/branching-strategy/`](docs/branching-strategy/) for the full
write-up. Short version: `main` is always deployable; work happens on
short-lived `feature/*` branches and gets merged back via PR.

