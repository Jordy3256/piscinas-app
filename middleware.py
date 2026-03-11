from django.http import HttpResponse

class HealthzMiddleware:
    """
    Responde /healthz y /healthz/ sin depender del urls.py (ideal para Render).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path == "/healthz" or path == "/healthz/":
            return HttpResponse("ok", content_type="text/plain")
        return self.get_response(request)