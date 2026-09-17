"""
Local development settings.

Used by default (see manage.py / wsgi.py / asgi.py). Run with:

    python manage.py runserver

or explicitly:

    DJANGO_SETTINGS_MODULE=unleased_project.settings.dev python manage.py runserver
"""

import os

from .base import *  # noqa: F401,F403

DEBUG = True

# Comma-separated list in .env, e.g. ALLOWED_HOSTS=localhost,127.0.0.1
ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
    if h.strip()
]
