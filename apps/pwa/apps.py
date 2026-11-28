from django.apps import AppConfig


class PwaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.pwa'
    verbose_name = 'اپلیکیشن وب (PWA)'

    def ready(self):
        from . import signals  # noqa: F401
