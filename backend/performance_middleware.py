"""Medición opcional de tiempo servidor para diagnosticar páginas lentas.

Activar temporalmente con JVAQUA_PERF_TIMING=true. No registra datos de clientes.
"""
import time

from django.conf import settings


class ServerTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "JVAQUA_PERF_TIMING", False):
            return self.get_response(request)
        inicio = time.perf_counter()
        response = self.get_response(request)
        transcurrido_ms = (time.perf_counter() - inicio) * 1000
        # Server-Timing se visualiza en DevTools > Network > Timing.
        response["Server-Timing"] = f"app;dur={transcurrido_ms:.1f}"
        return response
