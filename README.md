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
├── docs/
│   ├── wireframes/             # UI wireframes/mockups
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
6. (Optional) Load sample data:
   ```
   python manage.py createsuperuser   # if you need to log into /admin/
   python seed_data.py
   ```
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

## Branching strategy

See [`docs/branching-strategy/`](docs/branching-strategy/) for the full
write-up. Short version: `main` is always deployable; work happens on
short-lived `feature/*` branches and gets merged back via PR.

