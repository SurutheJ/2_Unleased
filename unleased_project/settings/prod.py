"""
Production settings.

Never run with DEBUG on in production — a stack trace with source code,
settings, and environment variables is a serious information leak.

Deploy with:

    DJANGO_SETTINGS_MODULE=unleased_project.settings.prod python manage.py runserver

(or whatever your WSGI/ASGI host sets as the settings module). In
production, ALLOWED_HOSTS and SECRET_KEY should come from real host
environment variables (Render/Railway/Heroku config vars, systemd
EnvironmentFile, etc.) rather than a committed .env file.
"""

import os

from .base import *  # noqa: F401,F403

DEBUG = False

# No default here on purpose — a production deploy with no ALLOWED_HOSTS
# set should fail loudly rather than silently accept requests from
# nowhere (empty list) or everywhere.
_allowed_hosts = os.environ.get('ALLOWED_HOSTS', '')
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts.split(',') if h.strip()]
if not ALLOWED_HOSTS:
    raise RuntimeError(
        "ALLOWED_HOSTS must be set via the environment when running with "
        "settings.prod (e.g. ALLOWED_HOSTS=unleased.example.com)."
    )

# ---- Baseline production hardening ----
# Safe defaults for an app served over HTTPS. Toggle off with env vars if
# a specific deploy target (e.g. behind a load balancer that already
# terminates TLS) needs different behavior.
# PythonAnywhere terminates HTTPS at its proxy and passes X-Forwarded-Proto,
# so request.build_absolute_uri() (used for the Vega-Lite spec URLs) gives https://.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
# Google only accepts https:// redirect URIs for a real domain, so any URL
# allauth builds without a request (e.g. in emails) must be https too.
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'https'
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# ---- Static file cache busting ----
# Appends a content hash to every static filename at `collectstatic` time
# (e.g. css/base.css -> css/base.3f2a91c4d8e2.css) and rewrites every
# {% static %} reference to match. Browsers can cache static files
# forever since the URL itself changes whenever the file's contents do —
# no manual version query strings to remember to bump.
#
# Uses the STORAGES setting (Django >=4.2) rather than the legacy
# STATICFILES_STORAGE name, which newer Django versions ignore.
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage',
    },
}
