"""Comunicados para trabajadores: envío deliberado por administrador."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from trabajadores.models import Trabajador
from .models import Notificacion
from .views import es_admin, _send_push_to_user


@login_required
def comunicados_view(request):
    if not es_admin(request.user):
        return HttpResponseForbidden('Solo administración puede enviar comunicados.')
    trabajadores = Trabajador.objects.filter(activo=True, user__is_active=True).select_related('user').order_by('user__username')
    if request.method == 'POST':
        titulo = (request.POST.get('titulo') or '').strip()
        contenido = (request.POST.get('mensaje') or '').strip()
        destinatario = (request.POST.get('destinatario') or 'todos').strip()
        if not titulo or not contenido or len(titulo) > 150 or len(contenido) > 2000:
            messages.error(request, 'Escribe un asunto (máximo 150 caracteres) y mensaje (máximo 2000).')
        else:
            if destinatario == 'todos':
                usuarios = [t.user for t in trabajadores]
            else:
                usuarios = [t.user for t in trabajadores if str(t.pk) == destinatario]
            if not usuarios:
                messages.error(request, 'Selecciona un destinatario válido.')
            else:
                creadas = []
                with transaction.atomic():
                    for user in usuarios:
                        creada = Notificacion.objects.create(user=user, titulo=titulo, mensaje=contenido,
                            url='/dashboard/notificaciones/', tipo='comunicado')
                        creadas.append((user, creada.pk))
                for user, pk in creadas:
                    _send_push_to_user(user, titulo, contenido, url='/dashboard/notificaciones/', tag=f'comunicado-{pk}')
                messages.success(request, f'Comunicado guardado para {len(creadas)} trabajador(es). El push se envía a dispositivos suscritos.')
                return redirect('comunicados')
    return render(request, 'dashboard/comunicados.html', {'trabajadores': trabajadores, 'base_template': 'dashboard/base_admin.html'})
