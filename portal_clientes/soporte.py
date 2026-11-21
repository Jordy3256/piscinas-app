"""Chat de soporte: separación estricta de permisos cliente / administración."""
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from io import BytesIO
from PIL import Image, UnidentifiedImageError
from django.db.models import Count, Q
from django.http import Http404, JsonResponse, HttpResponse
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


def _validar_archivo(archivo):
    if not archivo:
        return None
    if not isinstance(archivo, UploadedFile):
        raise ValidationError('Archivo no válido.')
    tipo = (archivo.content_type or '').lower().split(';')[0].strip()
    es_imagen = tipo in ('image/jpeg', 'image/png', 'image/webp')
    es_audio = tipo in ('audio/webm', 'video/webm', 'audio/ogg', 'audio/mp4', 'audio/mpeg', 'audio/wav', 'audio/x-wav', 'audio/aac')
    limite = 5 * 1024 * 1024 if es_imagen else 3 * 1024 * 1024
    if not (es_imagen or es_audio) or archivo.size > limite or archivo.size == 0:
        raise ValidationError('Formato no permitido o archivo demasiado grande (foto 5 MB, audio 3 MB).')
    datos = archivo.read(limite + 1)
    if len(datos) != archivo.size or len(datos) > limite:
        raise ValidationError('Tamaño de archivo inválido.')
    if es_imagen:
        try:
            imagen = Image.open(BytesIO(datos))
            imagen.verify()
            formatos = {'image/jpeg': 'JPEG', 'image/png': 'PNG', 'image/webp': 'WEBP'}
            if imagen.format != formatos[tipo]:
                raise ValueError('Formato no coincide')
        except (UnidentifiedImageError, OSError, ValueError):
            raise ValidationError('La fotografía no es una imagen válida.')
    else:
        valid = (
            (tipo in ('audio/webm', 'video/webm') and datos.startswith(b'\x1a\x45\xdf\xa3')) or
            (tipo == 'audio/ogg' and datos.startswith(b'OggS')) or
            (tipo == 'audio/mp4' and b'ftyp' in datos[:16]) or
            (tipo == 'audio/mpeg' and (datos.startswith(b'ID3') or datos[:1] == b'\xff')) or
            (tipo in ('audio/wav', 'audio/x-wav') and datos.startswith(b'RIFF') and datos[8:12] == b'WAVE') or
            (tipo == 'audio/aac' and datos[:1] == b'\xff')
        )
        if not valid:
            raise ValidationError('La grabación de audio no es válida.')
    return {'archivo': datos, 'archivo_tipo': tipo, 'archivo_clase': 'foto' if es_imagen else 'audio', 'archivo_nombre': ('foto' if es_imagen else 'audio')}


def _mensaje(request, conversacion, es_cliente):
    contenido = (request.POST.get('mensaje') or '').strip()
    if len(contenido) > 2000:
        return 'El mensaje no puede superar 2000 caracteres.'
    try:
        adjunto = _validar_archivo(request.FILES.get('archivo'))
    except ValidationError as exc:
        return '; '.join(exc.messages)
    if not contenido and not adjunto:
        return 'Escribe un mensaje o adjunta una fotografía o audio.'
    with transaction.atomic():
        MensajeSoporte.objects.create(conversacion=conversacion, autor=request.user, es_cliente=es_cliente, contenido=contenido, **(adjunto or {}))
        ConversacionSoporte.objects.filter(pk=conversacion.pk).update(actualizada_en=timezone.now())
    return None


def _archivo_respuesta(mensaje):
    if not mensaje.archivo or mensaje.archivo_clase not in ('foto', 'audio'):
        raise Http404('Adjunto no disponible')
    respuesta = HttpResponse(bytes(mensaje.archivo), content_type=mensaje.archivo_tipo)
    respuesta['Content-Disposition'] = 'inline; filename="%s"' % ('imagen' if mensaje.archivo_clase == 'foto' else 'audio')
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store'
    respuesta['Content-Security-Policy'] = "default-src 'none'; sandbox"
    return respuesta


@login_required(login_url='/portal/ingresar/')
@never_cache
@require_http_methods(['GET'])
def soporte_archivo_cliente(request, pk):
    acceso = _acceso(request)
    if not acceso:
        raise Http404('No disponible')
    mensaje = get_object_or_404(MensajeSoporte.objects.select_related('conversacion'), pk=pk, conversacion__cliente_id=acceso.cliente_id)
    return _archivo_respuesta(mensaje)


@login_required
@never_cache
@require_http_methods(['GET'])
def soporte_archivo_admin(request, pk):
    if not _admin(request):
        raise Http404('No disponible')
    mensaje = get_object_or_404(MensajeSoporte, pk=pk)
    return _archivo_respuesta(mensaje)


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
    return render(request, 'portal_clientes/soporte_chat.html', {'cliente': acceso.cliente, 'conversacion': conversacion, 'mensajes_chat': conversacion.mensajes.select_related('autor').defer('archivo'), 'error': error})


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
    return render(request, 'portal_clientes/soporte_admin_chat.html', {'conversacion': conversacion, 'mensajes_chat': conversacion.mensajes.select_related('autor').defer('archivo'), 'error': error})


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
    mensajes = list(conversacion.mensajes.defer('archivo').all())
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
