from zoneinfo import ZoneInfo

from django.utils import timezone


ECUADOR_TIME_ZONE = ZoneInfo("America/Guayaquil")


class EcuadorTimezoneMiddleware:
    """Activa explícitamente la zona horaria operativa de JVAQUA por petición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        timezone.activate(ECUADOR_TIME_ZONE)
        try:
            return self.get_response(request)
        finally:
            timezone.deactivate()
