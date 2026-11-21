"""Notificaciones internas del portal; derivadas de registros existentes, sin tocar la agenda."""
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from mantenimientos.models import Mantenimiento
from .models import AccesoCliente, NotificacionMantenimientoCliente, AvisoPortal

def _acceso(request):
    acceso = AccesoCliente.objects.filter(usuario=request.user, habilitado=True, cliente__activo=True).select_related('cliente').first()
    if not acceso:
        raise Http404
    return acceso

def _sincronizar(cliente_id):
    hoy = timezone.localdate()
    manana = hoy + timedelta(days=1)
    # Solo registros del cliente y contratos propios; no se crean mantenimientos.
    visitas = Mantenimiento.objects.filter(cliente_id=cliente_id, contrato__cliente_id=cliente_id).filter(
        Q(estado='pendiente', fecha=manana) |
        Q(estado='realizado', realizado_en__date__gte=hoy-timedelta(days=30))
    ).only('pk', 'cliente_id', 'estado', 'fecha', 'realizado_en')
    existentes = set(NotificacionMantenimientoCliente.objects.filter(cliente_id=cliente_id).values_list('mantenimiento_id','tipo'))
    nuevos = []
    for visita in visitas:
        if visita.estado == 'pendiente':
            tipos = ('proxima',)
        else:
            tipos = ('realizado',)
        for tipo in tipos:
            if (visita.pk,tipo) not in existentes:
                nuevos.append(NotificacionMantenimientoCliente(cliente_id=cliente_id,mantenimiento_id=visita.pk,tipo=tipo))
    if nuevos:
        NotificacionMantenimientoCliente.objects.bulk_create(nuevos, ignore_conflicts=True)

def _avisos(cliente_id):
    hoy = timezone.localdate()
    return NotificacionMantenimientoCliente.objects.filter(
        cliente_id=cliente_id, mantenimiento__cliente_id=cliente_id, mantenimiento__contrato__cliente_id=cliente_id
    ).filter(
        Q(tipo='proxima', mantenimiento__estado='pendiente', mantenimiento__fecha__gte=hoy) |
        Q(tipo='realizado', mantenimiento__estado='realizado')
    ).select_related('mantenimiento','mantenimiento__contrato')

def _datos(aviso):
    m=aviso.mantenimiento
    if aviso.tipo=='proxima':
        titulo='Próxima visita programada'
        detalle=f'Tu piscina tiene un mantenimiento programado para mañana, {m.fecha:%d/%m/%Y}.'
        destino='portal_clientes:proximas_visitas'
        return {'id':aviso.pk,'titulo':titulo,'detalle':detalle,'fecha':timezone.localtime(aviso.creada_en).strftime('%d/%m/%Y %H:%M'),'leida':bool(aviso.leida_en),'tipo':aviso.tipo}
    titulo='Mantenimiento completado'
    detalle='Tu mantenimiento fue registrado. Consulta las fotografías y el reporte completo desde este aviso.'
    return {'id':aviso.pk,'titulo':titulo,'detalle':detalle,'fecha':timezone.localtime(aviso.creada_en).strftime('%d/%m/%Y %H:%M'),'leida':bool(aviso.leida_en),'tipo':aviso.tipo}

def _sincronizar_cobros(cliente_id):
    """Solo la primera obligación impaga por contrato; vencidos cada 3 días (3,6,9...)."""
    from finanzas.models import Factura
    hoy=timezone.localdate()
    facturas=Factura.objects.filter(cliente_id=cliente_id,contrato__cliente_id=cliente_id).exclude(estado__in=['anulada','promocion']).prefetch_related('pagos').order_by('fecha_vencimiento','pk')
    primeras={}
    for f in facturas:
        if f.saldo <= 0: continue
        clave=(f.fecha_real_cobro,f.fecha_vencimiento,f.pk)
        if f.contrato_id not in primeras or clave < primeras[f.contrato_id][0]: primeras[f.contrato_id]=(clave,f)
    nuevos=[]
    for _,f in primeras.values():
        fecha=f.fecha_real_cobro
        if fecha == hoy:
            tipo='cobro';clave=f'cobro:{f.pk}:{hoy.isoformat()}'
            titulo='Hoy corresponde tu pago'
            detalle=f'Hoy corresponde el pago de la factura {f.numero}. Saldo pendiente: ${f.saldo:.2f}.'
        elif fecha < hoy and (hoy-fecha).days % 3 == 0:
            tipo='vencido';clave=f'ven:{f.pk}:{hoy.isoformat()}'
            titulo='Pago vencido'
            detalle=f'La factura {f.numero} tiene un saldo pendiente de ${f.saldo:.2f}. Puedes consultar el detalle en Mis pagos.'
        else: continue
        nuevos.append(AvisoPortal(cliente_id=cliente_id,clave=clave,tipo=tipo,titulo=titulo,detalle=detalle))
    if nuevos: AvisoPortal.objects.bulk_create(nuevos,ignore_conflicts=True)

def _generales(cliente_id):
    return AvisoPortal.objects.filter(cliente_id=cliente_id)

def _total_pendientes(cliente_id):
    return _avisos(cliente_id).filter(leida_en__isnull=True).count()+_generales(cliente_id).filter(leida_en__isnull=True).count()

@login_required(login_url='/portal/ingresar/')
@never_cache
@require_GET
def lista(request):
    acceso=_acceso(request)
    _sincronizar(acceso.cliente_id)
    _sincronizar_cobros(acceso.cliente_id)
    avisos=list(_avisos(acceso.cliente_id).order_by('-creada_en','-pk')[:50])
    generales=list(_generales(acceso.cliente_id).order_by('-creada_en','-pk')[:50])
    return render(request,'portal_clientes/notificaciones.html',{'cliente':acceso.cliente,'avisos':avisos,'generales':generales,'no_leidas':_total_pendientes(acceso.cliente_id)})

@login_required(login_url='/portal/ingresar/')
@never_cache
@require_GET
def contador(request):
    acceso=_acceso(request)
    _sincronizar(acceso.cliente_id)
    _sincronizar_cobros(acceso.cliente_id)
    return JsonResponse({'total':_total_pendientes(acceso.cliente_id)})

@login_required(login_url='/portal/ingresar/')
@never_cache
@require_POST
def abrir(request, pk):
    acceso=_acceso(request)
    aviso=get_object_or_404(_avisos(acceso.cliente_id),pk=pk)
    if aviso.leida_en is None:
        NotificacionMantenimientoCliente.objects.filter(pk=aviso.pk,cliente_id=acceso.cliente_id,leida_en__isnull=True).update(leida_en=timezone.now())
    if aviso.tipo=='proxima':
        return redirect('portal_clientes:proximas_visitas')
    return redirect('portal_clientes:mantenimiento_detalle',pk=aviso.mantenimiento_id)

@login_required(login_url='/portal/ingresar/')
@never_cache
@require_POST
def marcar_todas(request):
    acceso=_acceso(request)
    ids=list(_avisos(acceso.cliente_id).filter(leida_en__isnull=True).values_list('pk',flat=True))
    NotificacionMantenimientoCliente.objects.filter(cliente_id=acceso.cliente_id,pk__in=ids).update(leida_en=timezone.now())
    _generales(acceso.cliente_id).filter(leida_en__isnull=True).update(leida_en=timezone.now())
    return redirect('portal_clientes:notificaciones')

@login_required(login_url='/portal/ingresar/')
@never_cache
@require_POST
def abrir_general(request,pk):
    acceso=_acceso(request)
    aviso=get_object_or_404(_generales(acceso.cliente_id),pk=pk)
    if aviso.leida_en is None:
        _generales(acceso.cliente_id).filter(pk=pk,leida_en__isnull=True).update(leida_en=timezone.now())
    if aviso.tipo in ('cobro','vencido','pago'): return redirect('portal_clientes:mis_pagos')
    return redirect('portal_clientes:notificaciones')
