"""Chat de soporte: separación estricta de permisos cliente / administración."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods
from contratos.models import Contrato
from .models import AccesoCliente, ConversacionSoporte, MensajeSoporte


def _acceso(request):
    return AccesoCliente.objects.select_related('cliente').filter(usuario=request.user, habilitado=True, cliente__activo=True).first()


def _admin(request):
    from dashboard.views import es_admin
    return es_admin(request.user) and not AccesoCliente.objects.filter(usuario=request.user).exists()


def _mensaje(request, conversacion, es_cliente):
    contenido = (request.POST.get('mensaje') or '').strip()
    if not contenido or len(contenido) > 2000:
        return 'Escribe un mensaje de entre 1 y 2000 caracteres.'
    with transaction.atomic():
        MensajeSoporte.objects.create(conversacion=conversacion, autor=request.user, es_cliente=es_cliente, contenido=contenido)
        ConversacionSoporte.objects.filter(pk=conversacion.pk).update(actualizada_en=timezone.now())
    return None


@login_required(login_url='/portal/ingresar/')
@never_cache
@require_http_methods(['GET', 'POST'])
def soporte_cliente(request):
    acceso = _acceso(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    contratos = Contrato.objects.filter(cliente_id=acceso.cliente_id).order_by('pk')
    conversaciones = ConversacionSoporte.objects.filter(cliente_id=acceso.cliente_id).select_related('contrato')
    error = None
    if request.method == 'POST':
        contrato_id = (request.POST.get('contrato') or '').strip()
        if contrato_id and (not contrato_id.isdecimal() or not contratos.filter(pk=int(contrato_id)).exists()):
            raise Http404('Contrato no disponible')
        if not contrato_id:
            contrato_id = None
        # Una conversación por cliente y contrato (o general), con bloqueo para evitar duplicados.
        with transaction.atomic():
            AccesoCliente.objects.select_for_update().get(pk=acceso.pk)
            conversacion = ConversacionSoporte.objects.filter(cliente_id=acceso.cliente_id, contrato_id=contrato_id).first()
            if conversacion is None:
                conversacion = ConversacionSoporte.objects.create(cliente_id=acceso.cliente_id, contrato_id=contrato_id)
        error = _mensaje(request, conversacion, True)
        if error is None:
            return redirect('portal_clientes:soporte_conversacion', pk=conversacion.pk)
    return render(request, 'portal_clientes/soporte_lista.html', {'cliente': acceso.cliente, 'contratos': contratos, 'conversaciones': conversaciones, 'error': error})


@login_required(login_url='/portal/ingresar/')
@never_cache
@require_http_methods(['GET', 'POST'])
def soporte_conversacion(request, pk):
    acceso = _acceso(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    conversacion = get_object_or_404(ConversacionSoporte.objects.select_related('contrato'), pk=pk, cliente_id=acceso.cliente_id)
    error = None
    if request.method == 'POST':
        error = _mensaje(request, conversacion, True)
        if error is None:
            return redirect('portal_clientes:soporte_conversacion', pk=pk)
    MensajeSoporte.objects.filter(conversacion=conversacion, es_cliente=False, leido_en__isnull=True).update(leido_en=timezone.now())
    return render(request, 'portal_clientes/soporte_chat.html', {'cliente': acceso.cliente, 'conversacion': conversacion, 'mensajes_chat': conversacion.mensajes.select_related('autor'), 'error': error})


@login_required
@never_cache
@require_http_methods(['GET'])
def soporte_admin_lista(request):
    if not _admin(request):
        return render(request, 'dashboard/no_autorizado.html', status=403)
    conversaciones = ConversacionSoporte.objects.select_related('cliente', 'contrato').annotate(
        sin_leer=Count('mensajes', filter=Q(mensajes__es_cliente=True, mensajes__leido_en__isnull=True))
    )[:100]
    return render(request, 'portal_clientes/soporte_admin_lista.html', {'conversaciones': conversaciones})


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def soporte_admin_chat(request, pk):
    if not _admin(request):
        return render(request, 'dashboard/no_autorizado.html', status=403)
    conversacion = get_object_or_404(ConversacionSoporte.objects.select_related('cliente', 'contrato'), pk=pk)
    error = None
    if request.method == 'POST':
        error = _mensaje(request, conversacion, False)
        if error is None:
            return redirect('soporte_admin_chat', pk=pk)
    MensajeSoporte.objects.filter(conversacion=conversacion, es_cliente=True, leido_en__isnull=True).update(leido_en=timezone.now())
    return render(request, 'portal_clientes/soporte_admin_chat.html', {'conversacion': conversacion, 'mensajes_chat': conversacion.mensajes.select_related('autor'), 'error': error})


@login_required(login_url='/portal/ingresar/')
@never_cache
@require_http_methods(['GET'])
def soporte_actualizaciones(request, pk):
    """Consulta ligera para refrescar el chat; nunca expone mensajes ajenos."""
    if request.GET.get('lado') == 'admin':
        if not _admin(request):
            return JsonResponse({'error': 'No autorizado'}, status=403)
        conversacion = get_object_or_404(ConversacionSoporte, pk=pk)
        es_cliente = False
    else:
        acceso = _acceso(request)
        if not acceso:
            return JsonResponse({'error': 'No autorizado'}, status=403)
        conversacion = get_object_or_404(ConversacionSoporte, pk=pk, cliente_id=acceso.cliente_id)
        es_cliente = True
    # Marcar como leídos únicamente cuando el usuario mantiene abierto el chat.
    MensajeSoporte.objects.filter(conversacion=conversacion, es_cliente=not es_cliente, leido_en__isnull=True).update(leido_en=timezone.now())
    mensajes = list(conversacion.mensajes.all())
    html = render_to_string('portal_clientes/soporte_mensajes.html', {'mensajes_chat': mensajes, 'es_cliente_actual': es_cliente}, request=request)
    return JsonResponse({'html': html, 'ultimo_id': mensajes[-1].pk if mensajes else 0})


@login_required(login_url='/portal/ingresar/')
@never_cache
@require_http_methods(['GET'])
def soporte_contadores(request):
    """Contadores agregados por usuario y conversación, sin filtrar contenido."""
    if request.GET.get('lado') == 'admin':
        if not _admin(request):
            return JsonResponse({'error': 'No autorizado'}, status=403)
        mensajes = MensajeSoporte.objects.filter(es_cliente=True, leido_en__isnull=True)
    else:
        acceso = _acceso(request)
        if not acceso:
            return JsonResponse({'error': 'No autorizado'}, status=403)
        mensajes = MensajeSoporte.objects.filter(conversacion__cliente_id=acceso.cliente_id, es_cliente=False, leido_en__isnull=True)
    por_chat = {str(item['conversacion_id']): item['total'] for item in mensajes.values('conversacion_id').annotate(total=Count('pk'))}
    return JsonResponse({'total': sum(por_chat.values()), 'conversaciones': por_chat})
