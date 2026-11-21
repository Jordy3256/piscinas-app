"""Comunicados a clientes desde el ERP; no altera el módulo de trabajadores."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseForbidden, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from clientes.models import Ciudad, Cliente
from portal_clientes.models import AccesoCliente, AvisoPortal, ComunicadoPortal
from .views import es_admin


def _permitido(user):
    return es_admin(user) and not AccesoCliente.objects.filter(usuario=user).exists() and (
        user.is_superuser or user.has_perm('portal_clientes.add_comunicadoportal')
    )


def _destinatarios(comunicado):
    qs = Cliente.objects.filter(activo=True, acceso_portal__habilitado=True,
                                acceso_portal__usuario__isnull=False,
                                acceso_portal__usuario__is_active=True)
    if comunicado.destino == 'ciudad':
        return qs.filter(ciudad_ref_id=comunicado.ciudad_id)
    if comunicado.destino == 'cliente':
        return qs.filter(pk=comunicado.cliente_id)
    return qs


@login_required
@require_http_methods(['GET', 'POST'])
def comunicados_clientes(request):
    if not _permitido(request.user):
        return HttpResponseForbidden('Sin permisos para comunicados de clientes.')
    if request.method == 'POST':
        titulo = (request.POST.get('titulo') or '').strip()
        contenido = (request.POST.get('contenido') or '').strip()
        destino = (request.POST.get('destino') or '').strip()
        accion = request.POST.get('accion')
        ciudad_id = request.POST.get('ciudad') or None
        cliente_id = request.POST.get('cliente') or None
        if not titulo or not contenido or len(titulo) > 160 or len(contenido) > 1500 or destino not in ('todos','ciudad','cliente'):
            messages.error(request, 'Revisa el título, el mensaje y los destinatarios.')
        elif accion not in ('borrador','publicar'):
            messages.error(request, 'Acción no válida.')
        elif accion == 'publicar' and not (request.user.is_superuser or request.user.has_perm('portal_clientes.change_comunicadoportal')):
            messages.error(request, 'Sin permisos para publicar.')
        elif destino == 'ciudad' and not Ciudad.objects.filter(pk=ciudad_id).exists():
            messages.error(request, 'Selecciona una ciudad válida.')
        elif destino == 'cliente' and not Cliente.objects.filter(pk=cliente_id).exists():
            messages.error(request, 'Selecciona un cliente válido.')
        else:
            with transaction.atomic():
                comunicado = ComunicadoPortal.objects.create(
                    titulo=titulo, contenido=contenido, destino=destino,
                    ciudad_id=ciudad_id if destino == 'ciudad' else None,
                    cliente_id=cliente_id if destino == 'cliente' else None)
                if accion == 'publicar':
                    cantidad = _publicar(comunicado)
                    messages.success(request, f'Comunicado publicado para {cantidad} cliente(s) con portal activo.')
                else:
                    messages.success(request, 'Borrador guardado. Aún no se ha enviado.')
            return redirect('comunicados_clientes')
    return render(request, 'dashboard/comunicados_clientes.html', {
        'ciudades': Ciudad.objects.filter(activa=True),
        'clientes': Cliente.objects.filter(activo=True).order_by('nombre').only('id','nombre','ciudad'),
        'comunicados': ComunicadoPortal.objects.select_related('ciudad','cliente').order_by('-creado_en')[:100],
    })


def _publicar(comunicado):
    # La transacción y bloqueo se comparten con la acción del administrador Django.
    actual = ComunicadoPortal.objects.select_for_update().get(pk=comunicado.pk)
    if actual.publicado_en:
        return 0
    ids = list(_destinatarios(actual).values_list('pk', flat=True))
    AvisoPortal.objects.bulk_create([
        AvisoPortal(cliente_id=cid, clave=f'comunicado:{actual.pk}', tipo='comunicado',
                    titulo=actual.titulo, detalle=actual.contenido)
        for cid in ids
    ], ignore_conflicts=True, batch_size=500)
    actual.publicado_en = timezone.now()
    actual.save(update_fields=['publicado_en'])
    return len(ids)


@login_required
@require_http_methods(['POST'])
def publicar_borrador_clientes(request, pk):
    if not _permitido(request.user) or not (request.user.is_superuser or request.user.has_perm('portal_clientes.change_comunicadoportal')):
        return HttpResponseForbidden('Sin permisos para publicar.')
    with transaction.atomic():
        comunicado = get_object_or_404(ComunicadoPortal.objects.select_for_update(), pk=pk)
        if comunicado.publicado_en:
            messages.warning(request, 'Este comunicado ya fue publicado.')
        else:
            cantidad = _publicar(comunicado)
            messages.success(request, f'Comunicado publicado para {cantidad} cliente(s) con portal activo.')
    return redirect('comunicados_clientes')
