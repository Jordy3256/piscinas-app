from django.http import HttpResponseForbidden


class PortalClientAreaGuard:
    """Bloquea el ERP interno para usuarios vinculados al portal de clientes."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith(('/dashboard/', '/admin/')) and request.user.is_authenticated:
            from portal_clientes.models import AccesoCliente
            if AccesoCliente.objects.filter(usuario_id=request.user.pk).exists():
                return HttpResponseForbidden('Acceso exclusivo para el personal de JVAQUA.')
        return self.get_response(request)
