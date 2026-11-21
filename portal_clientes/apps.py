from django.apps import AppConfig

class PortalClientesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal_clientes'

    def ready(self):
        from . import signals  # noqa: F401
