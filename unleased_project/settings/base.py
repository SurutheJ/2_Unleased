"""
Base settings for the unleased_project project.

Holds everything that is IDENTICAL across every environment (installed
apps, middleware, templates, database engine, etc.). Anything that
differs between local development and production — DEBUG, ALLOWED_HOSTS,
security headers — lives in dev.py / prod.py instead, which both import
* from this file.

Secrets (SECRET_KEY, API keys) are never hardcoded here. They're read
from environment variables, which are loaded from a local .env file via
python-dotenv. See .env.example for the full list of variables a
teammate needs to set.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# unleased_project/settings/base.py -> settings/ -> unleased_project/ -> project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load variables from a .env file in the project root (if present).
# In production, real environment variables (set by the host) take
# precedence over anything in .env — load_dotenv() never overrides a
# variable that's already set in the environment.
load_dotenv(BASE_DIR / '.env')


def get_env(name, default=None, required=False):
    """Small helper so a missing required secret fails loudly and early,
    instead of Django crashing later with a confusing error."""
    value = os.environ.get(name, default)
    if required and not value:
        raise RuntimeError(
            f"Required environment variable '{name}' is not set. "
            f"Copy .env.example to .env and fill it in."
        )
    return value


# ---- Secrets (from environment / .env — never hardcoded) ----
SECRET_KEY = get_env('SECRET_KEY', required=True)

# Example of a third-party API key read the same way. Add real ones here
# as the project grows — never commit the actual value, only the
# placeholder in .env.example.
MAPS_API_KEY = get_env('MAPS_API_KEY', default='')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Unleased apps
    'accounts',
    'listings',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'unleased_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'unleased_project.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Point Django to our custom user model
AUTH_USER_MODEL = 'accounts.UnleasedUser'
