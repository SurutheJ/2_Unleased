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
    'django.contrib.sites',          # required by django-allauth
    # Authentication (A5): username/password login + Google OAuth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
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
    'allauth.account.middleware.AccountMiddleware',
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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'America/Chicago'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
# Project-level static source (CSS/JS/images we author) vs. STATIC_ROOT
# below, which is only the `collectstatic` output for deployment.
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Point Django to our custom user model
AUTH_USER_MODEL = 'accounts.UnleasedUser'


# ---------------------------------------------------------------------------
# Authentication (A5) - django-allauth
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    # Username/password login (also used by the /admin/ login)
    'django.contrib.auth.backends.ModelBackend',
    # allauth: lets users log in with username OR email, and (Part 2) Google
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1  # django.contrib.sites, needed by allauth

# Where @login_required / LoginRequiredMixin send logged-out users,
# and where users land after logging in or out.
LOGIN_URL = 'account_login'
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'home'
ACCOUNT_LOGOUT_REDIRECT_URL = 'home'

ACCOUNT_LOGIN_METHODS = {'username', 'email'}     # log in with either one
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none'   # no email server yet; .edu check is in accounts/signals.py
ACCOUNT_LOGOUT_ON_GET = False         # logging out needs a POST (with CSRF), not just a link
ACCOUNT_SESSION_REMEMBER = None       # show the "Remember me" checkbox

# No mail server: any email allauth would send (e.g. password reset) is
# printed to the console instead of failing.
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'


# ---------------------------------------------------------------------------
# Google OAuth (A5 Part 2)
# ---------------------------------------------------------------------------
# The Google client ID/secret live in .env (locally) or the host's real
# environment / a .env file next to manage.py (PythonAnywhere) - never in the
# admin panel, never in git. Because the app is defined here in settings,
# do NOT also add a "Social application" for Google in /admin/ (allauth would
# then find two Google apps and raise MultipleObjectsReturned).
GOOGLE_CLIENT_ID = get_env('GOOGLE_CLIENT_ID', default='')
GOOGLE_CLIENT_SECRET = get_env('GOOGLE_CLIENT_SECRET', default='')
GOOGLE_LOGIN_ENABLED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        # Only register the app when both values are present, so a machine
        # without Google keys still runs (the button is simply hidden).
        **({
            'APP': {
                'client_id': GOOGLE_CLIENT_ID,
                'secret': GOOGLE_CLIENT_SECRET,
                'key': '',
            },
        } if GOOGLE_LOGIN_ENABLED else {}),
    },
}

# Google has already verified the address, so an existing local account with
# the same email is signed in instead of failing with "email already in use".
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_AUTO_SIGNUP = True
