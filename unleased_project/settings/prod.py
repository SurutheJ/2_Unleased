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
SECURE_SSL_REDIRECT = os.environ.get('SECURE_SSL_REDIRECT', 'True') == 'True'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
