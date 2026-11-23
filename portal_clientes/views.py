from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import FileResponse, Http404
from django.views.decorators.cache import never_cache
from mantenimientos.models import FotoMantenimiento
from mantenimientos.models import Mantenimiento
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from clientes.models import Cliente
from contratos.models import Contrato
from .models import AccesoCliente

MENSAJE = 'No se pudo completar la solicitud. Compruebe los datos o contacte con JVAQUA.'

@never_cache
@require_http_methods(['GET', 'POST'])
def activar(request):
    """Segunda etapa de activación: código validado en el acceso principal."""
    from datetime import timedelta
    from django.contrib.auth.password_validation import validate_password
    from django.core.exceptions import ValidationError

    acceso_id = request.session.get('portal_activacion_id')
    verificado_en = request.session.get('portal_activacion_verificada_en', 0)
    valido = bool(acceso_id and verificado_en and
                  timezone.now().timestamp() - float(verificado_en) <= 900)
    if not valido:
        request.session.pop('portal_activacion_id', None)
        request.session.pop('portal_activacion_verificada_en', None)
        return redirect('/login/')
    error = None
    if request.method == 'POST':
        password = request.POST.get('password') or ''
        confirmacion = request.POST.get('confirmacion') or ''
        if password != confirmacion:
            error = 'Las contraseñas no coinciden.'
        elif len(password) < 12:
            error = 'La contraseña debe contener al menos 12 caracteres.'
        else:
            try:
                validate_password(password)
            except ValidationError as exc:
                error = ' '.join(exc.messages)
        if not error:
            with transaction.atomic():
                acceso = AccesoCliente.objects.select_for_update().select_related('cliente').filter(pk=acceso_id).first()
                if acceso and acceso.codigo_valido() and acceso.cliente.activo:
                    User = get_user_model()
                    usuario = User(username=f'portal_cliente_{acceso.cliente_id}', is_active=True)
                    usuario.set_password(password)
                    usuario.save()
                    acceso.usuario = usuario
                    acceso.codigo_hash = ''
                    acceso.codigo_expira = None
                    acceso.activado_en = timezone.now()
                    acceso.save(update_fields=['usuario', 'codigo_hash', 'codigo_expira', 'activado_en'])
                    request.session.pop('portal_activacion_id', None)
                    request.session.pop('portal_activacion_verificada_en', None)
                    return redirect('/login/')
                error = MENSAJE
    return render(request, 'portal_clientes/activar.html', {'error': error})

@require_http_methods(['GET', 'POST'])
def ingresar(request):
    """Ruta antigua conservada, pero el ingreso es siempre por el acceso principal."""
    return redirect('/login/')

@login_required(login_url='/portal/ingresar/')
def inicio(request):
    acceso = AccesoCliente.objects.select_related('cliente').filter(usuario=request.user, habilitado=True, cliente__activo=True).first()
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    contratos = Contrato.objects.filter(cliente_id=acceso.cliente_id).order_by('-id')
    hoy = timezone.localdate()
    visitas_cliente = Mantenimiento.objects.filter(
        cliente_id=acceso.cliente_id, contrato__cliente_id=acceso.cliente_id
    )
    ultimo = (visitas_cliente.filter(estado='realizado', fecha__lte=hoy)
              .order_by('-fecha', '-pk').first())
    proxima = (visitas_cliente.filter(estado='pendiente', fecha__gte=hoy)
               .order_by('fecha', 'pk').first())
    return render(request, 'portal_clientes/inicio.html', {
        'cliente': acceso.cliente, 'contratos': contratos,
        'ultimo_mantenimiento': ultimo, 'proxima_visita': proxima,
    })

@require_http_methods(['POST'])
def salir(request):
    logout(request)
    return redirect('/login/')


def _acceso_vigente(request):
    return AccesoCliente.objects.select_related('cliente').filter(
        usuario=request.user, habilitado=True, cliente__activo=True
    ).first()


@login_required(login_url='/portal/ingresar/')
def mantenimientos(request):
    acceso = _acceso_vigente(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    # Filtrar SIEMPRE por contrato y cliente para prevenir cruces de registros.
    registros = Mantenimiento.objects.filter(
        cliente_id=acceso.cliente_id,
        contrato__cliente_id=acceso.cliente_id,
    ).filter(
        Q(fecha__lt=timezone.localdate()) |
        Q(fecha=timezone.localdate(), estado__in=['realizado', 'cancelado'])
    ).select_related('contrato').order_by('-fecha', '-pk')
    pagina = Paginator(registros, 20).get_page(request.GET.get('pagina'))
    return render(request, 'portal_clientes/mantenimientos.html', {
        'cliente': acceso.cliente, 'pagina': pagina,
    })


@login_required(login_url='/portal/ingresar/')
def mantenimiento_detalle(request, pk):
    acceso = _acceso_vigente(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    mantenimiento = get_object_or_404(
        Mantenimiento.objects.select_related('contrato'),
        pk=pk, cliente_id=acceso.cliente_id, contrato__cliente_id=acceso.cliente_id,
    )
    checklist = getattr(mantenimiento, 'checklist_v2', None)
    fotos = list(mantenimiento.fotos.order_by('creada_en', 'pk')) if mantenimiento.estado == 'realizado' else []
    usos = list(mantenimiento.usos_insumos.select_related('insumo').order_by('pk')) if mantenimiento.estado == 'realizado' else []
    return render(request, 'portal_clientes/mantenimiento_detalle.html', {
        'cliente': acceso.cliente, 'mantenimiento': mantenimiento, 'checklist': checklist, 'fotos': fotos, 'usos': usos,
    })


@login_required(login_url='/portal/ingresar/')
def proximas_visitas(request):
    acceso = _acceso_vigente(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    visitas = Mantenimiento.objects.filter(
        cliente_id=acceso.cliente_id,
        contrato__cliente_id=acceso.cliente_id,
        estado='pendiente',
        fecha__gte=timezone.localdate(),
    ).select_related('contrato').order_by('fecha', 'pk')
    pagina = Paginator(visitas, 20).get_page(request.GET.get('pagina'))
    return render(request, 'portal_clientes/proximas_visitas.html', {
        'cliente': acceso.cliente, 'pagina': pagina,
    })


@never_cache
@login_required(login_url='/portal/ingresar/')
def foto_mantenimiento(request, pk, foto_id):
    """Lectura de evidencias mediante permisos por cliente, contrato y mantenimiento.

    No publica ni expone la URL del proveedor de almacenamiento.
    """
    acceso = _acceso_vigente(request)
    if not acceso:
        raise Http404
    foto = get_object_or_404(
        FotoMantenimiento.objects.select_related('mantenimiento'),
        pk=foto_id, mantenimiento_id=pk,
        mantenimiento__cliente_id=acceso.cliente_id,
        mantenimiento__contrato__cliente_id=acceso.cliente_id,
        mantenimiento__estado='realizado',
    )
    if not foto.imagen or not foto.imagen.name:
        raise Http404
    try:
        archivo = foto.imagen.open('rb')
    except (OSError, IOError, ValueError):
        raise Http404
    respuesta = FileResponse(archivo, content_type='image/jpeg')
    respuesta['Content-Disposition'] = 'inline'
    respuesta['X-Content-Type-Options'] = 'nosniff'
    respuesta['Cache-Control'] = 'private, no-store, max-age=0'
    respuesta['Referrer-Policy'] = 'no-referrer'
    return respuesta


@login_required(login_url='/portal/ingresar/')
@never_cache
def mis_pagos(request):
    """Consulta financiera de solo lectura, limitada a contratos propios."""
    from decimal import Decimal
    from django.db.models import Prefetch
    from finanzas.models import Factura, PagoFactura

    acceso = _acceso_vigente(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    contratos = Contrato.objects.filter(cliente_id=acceso.cliente_id).order_by('pk')
    contrato_ids = list(contratos.values_list('pk', flat=True))
    seleccion = (request.GET.get('contrato') or '').strip()
    if seleccion and (not seleccion.isdecimal() or int(seleccion) not in contrato_ids):
        raise Http404('Contrato no disponible')
    if seleccion:
        contrato_ids = [int(seleccion)]
    facturas = list(Factura.objects.filter(
        cliente_id=acceso.cliente_id, contrato_id__in=contrato_ids
    ).select_related('contrato').prefetch_related(
        Prefetch('pagos', queryset=PagoFactura.objects.filter(activo=True).order_by('-fecha', '-pk'))
    ).order_by('-fecha_vencimiento', '-pk'))
    hoy = timezone.localdate()
    from .conciliacion import resumir_facturas
    filas = []
    for factura in facturas:
        if factura.estado == Factura.ESTADO_ANULADA:
            continue
        restante = factura.saldo
        pagos_activos = [p for p in factura.pagos.all() if p.activo]
        filas.append({
            'factura': factura, 'saldo': restante, 'pagado': factura.monto_pagado,
            'vencida': restante > 0 and factura.fecha_real_cobro <= hoy and factura.fecha_vencimiento < hoy,
            'pagos': pagos_activos,
        })
    proximas, historial, saldo, vencido, pagado = resumir_facturas(filas, hoy)
    pagina = Paginator(historial, 15).get_page(request.GET.get('pagina'))
    return render(request, 'portal_clientes/mis_pagos.html', {
        'cliente': acceso.cliente, 'contratos': contratos, 'seleccion': seleccion,
        'saldo': saldo, 'vencido': vencido, 'pagado': pagado,
        'pagina': pagina, 'proximas': proximas,
    })


@login_required(login_url='/portal/ingresar/')
@never_cache
def mi_contrato(request, pk):
    """Ficha contractual de solo lectura; nunca permite consultar contratos ajenos."""
    from finanzas.models import Factura

    acceso = _acceso_vigente(request)
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    contrato = get_object_or_404(Contrato, pk=pk, cliente_id=acceso.cliente_id)
    hoy = timezone.localdate()
    facturas = Factura.objects.filter(
        cliente_id=acceso.cliente_id, contrato_id=contrato.pk
    ).exclude(estado=Factura.ESTADO_ANULADA).order_by('periodo_inicio', 'pk')
    periodo_actual = None
    proximo_periodo = None
    proxima_factura = None
    for factura in facturas:
        if factura.periodo_inicio and factura.periodo_fin:
            if factura.periodo_inicio <= hoy < factura.periodo_fin:
                if periodo_actual is None or factura.periodo_inicio > periodo_actual.periodo_inicio:
                    periodo_actual = factura
            elif factura.periodo_inicio > hoy:
                if proximo_periodo is None or factura.periodo_inicio < proximo_periodo.periodo_inicio:
                    proximo_periodo = factura
        if factura.saldo > 0:
            if proxima_factura is None or (factura.fecha_real_cobro, factura.fecha_vencimiento, factura.pk) < (proxima_factura.fecha_real_cobro, proxima_factura.fecha_vencimiento, proxima_factura.pk):
                proxima_factura = factura
    return render(request, 'portal_clientes/mi_contrato.html', {
        'cliente': acceso.cliente, 'contrato': contrato, 'periodo_actual': periodo_actual,
        'proximo_periodo': proximo_periodo, 'proxima_factura': proxima_factura,
    })
