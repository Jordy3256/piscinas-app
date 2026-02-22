from django.http import HttpResponse


class HealthzMiddleware:
    """
    Responde /healthz y /healthz/ sin depender del urls.py (ideal para Render).
    """

    def _init_(self, get_response):
        self.get_response = get_response

    def _call_(self, request):
        path = request.path  # ej: "/healthz/" o "/healthz"
        if path == "/healthz" or path == "/healthz/":
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)