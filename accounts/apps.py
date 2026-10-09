from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

    def ready(self):
        # Connect the edu_email sync signal (accounts/signals.py).
        from . import signals  # noqa: F401
