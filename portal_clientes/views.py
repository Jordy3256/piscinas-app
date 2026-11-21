from django.contrib.auth import get_user_model, login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import check_password
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from mantenimientos.models import Mantenimiento
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from clientes.models import Cliente
from contratos.models import Contrato
from .models import AccesoCliente

MENSAJE = 'No se pudo completar la solicitud. Compruebe los datos o contacte con JVAQUA.'

@require_http_methods(['GET', 'POST'])
def activar(request):
    error = None
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        codigo = (request.POST.get('codigo') or '').strip()
        password = request.POST.get('password') or ''
        if len(password) < 12:
            error = 'La contraseña debe contener al menos 12 caracteres.'
        else:
            with transaction.atomic():
                clientes = list(Cliente.objects.select_for_update().filter(email__iexact=email, activo=True)[:2])
                if len(clientes) == 1:
                    acceso = AccesoCliente.objects.select_for_update().filter(cliente=clientes[0]).first()
                    if acceso and acceso.codigo_valido() and check_password(codigo, acceso.codigo_hash):
                        User = get_user_model()
                        user = User(username=f'portal_cliente_{clientes[0].pk}', is_active=True)
                        user.set_password(password)
                        user.save()
                        acceso.usuario = user
                        acceso.codigo_hash = ''
                        acceso.codigo_expira = None
                        acceso.activado_en = timezone.now()
                        acceso.save(update_fields=['usuario','codigo_hash','codigo_expira','activado_en'])
                        return redirect('portal_clientes:ingresar')
                error = MENSAJE
    return render(request, 'portal_clientes/activar.html', {'error': error})

@require_http_methods(['GET','POST'])
def ingresar(request):
    error = None
    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip()
        password = request.POST.get('password') or ''
        clientes = list(Cliente.objects.filter(email__iexact=email, activo=True)[:2])
        if len(clientes) == 1:
            acceso = AccesoCliente.objects.select_related('usuario').filter(cliente=clientes[0], habilitado=True).first()
            if acceso and acceso.usuario_id and acceso.usuario.is_active:
                user = authenticate(request, username=acceso.usuario.username, password=password)
                if user is not None:
                    login(request, user)
                    return redirect('portal_clientes:inicio')
        error = 'Credenciales incorrectas.'
    return render(request, 'portal_clientes/ingresar.html', {'error':error})

@login_required(login_url='/portal/ingresar/')
def inicio(request):
    acceso = AccesoCliente.objects.select_related('cliente').filter(usuario=request.user, habilitado=True, cliente__activo=True).first()
    if not acceso:
        return render(request, 'portal_clientes/sin_acceso.html', status=403)
    contratos = Contrato.objects.filter(cliente_id=acceso.cliente_id).order_by('-id')
    return render(request, 'portal_clientes/inicio.html', {'cliente':acceso.cliente, 'contratos':contratos})

@require_http_methods(['POST'])
def salir(request):
    logout(request)
    return redirect('portal_clientes:ingresar')


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
    return render(request, 'portal_clientes/mantenimiento_detalle.html', {
        'cliente': acceso.cliente, 'mantenimiento': mantenimiento, 'checklist': checklist,
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
