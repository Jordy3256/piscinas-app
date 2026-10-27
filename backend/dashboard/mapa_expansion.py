"""Mapa administrativo de piscinas; reutiliza el geocodificador de rutas.

No modifica enlaces, direcciones ni coordenadas previamente almacenadas.
"""
import logging
import os
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render

from contratos.models import Contrato
from dashboard.views import _geocodificar_contrato_google

logger = logging.getLogger(__name__)


def _coordenadas_validas(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
        return (lat, lon) if -90 <= lat <= 90 and -180 <= lon <= 180 else None
    except (TypeError, ValueError, OverflowError):
        return None


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def mapa_expansion_view(request):
    modo = request.GET.get('modo', 'activos')
    if modo not in ('activos', 'historial', 'todos'):
        modo = 'activos'
    ciudad = (request.GET.get('ciudad') or '').strip()[:100]
    fecha_raw = (request.GET.get('fecha') or '').strip()
    try:
        fecha_consulta = date.fromisoformat(fecha_raw) if fecha_raw else None
    except ValueError:
        fecha_consulta = None

    qs = Contrato.objects.select_related('cliente', 'ciudad_ref', 'tecnico_designado').order_by('id')
    if fecha_consulta:
        # Reconstrucción limitada a vigencias registradas: el campo activo actual
        # no representa por sí solo el estado en una fecha anterior.
        inicio = Q(fecha_inicio_original__lte=fecha_consulta) | Q(
            fecha_inicio_original__isnull=True, fecha_inicio__lte=fecha_consulta)
        fin = Q(fecha_fin_contrato__isnull=True) | Q(fecha_fin_contrato__gte=fecha_consulta)
        vigentes = inicio & fin
        if modo == 'activos':
            qs = qs.filter(vigentes)
        elif modo == 'historial':
            qs = qs.filter(inicio).exclude(vigentes)
        else:
            qs = qs.filter(inicio)
    elif modo == 'activos':
        qs = qs.filter(activo=True)
    elif modo == 'historial':
        qs = qs.filter(activo=False)
    ciudades = sorted({(c.ciudad or (str(c.ciudad_ref) if c.ciudad_ref_id else '')).strip()
                      for c in Contrato.objects.select_related('ciudad_ref').only('ciudad', 'ciudad_ref')
                      if c.ciudad or c.ciudad_ref_id})
    if ciudad:
        qs = qs.filter(Q(ciudad__iexact=ciudad) | Q(ciudad_ref__nombre__iexact=ciudad))

    puntos, pendientes = [], []
    # El geocodificador de rutas persiste coordenadas de contrato, no las del cliente.
    # Limitar las resoluciones por carga evita ráfagas de peticiones externas y costos.
    limite = 8
    resueltos = 0
    api_key = os.environ.get('GOOGLE_MAPS_API_KEY', '').strip()
    for c in qs:
        coords = _coordenadas_validas(c.latitud, c.longitud)
        # Sin una referencia específica no se intenta geocodificar por ciudad:
        # ubicar todas las piscinas en el centro de una ciudad sería engañoso.
        cliente = c.cliente
        tiene_referencia = any(str(v or '').strip() for v in (
            c.enlace_google_maps, c.direccion,
            getattr(cliente, 'enlace_google_maps', ''),
            getattr(cliente, 'direccion', ''),
        ))
        if not coords and limite and tiene_referencia:
            limite -= 1
            try:
                resultado = _geocodificar_contrato_google(c, api_key)
                if resultado:
                    coords = _coordenadas_validas(resultado.get('lat'), resultado.get('lng'))
                    if coords:
                        resueltos += 1
            except Exception:
                logger.exception('No se pudo resolver GPS del contrato %s en mapa', c.pk)
        if not coords:
            pendientes.append({'id': c.pk, 'cliente': str(c.cliente),
                               'sector': c.sector_urbanizacion or 'Sin sector'})
            continue
        lat, lon = coords
        puntos.append({
            'id': c.pk, 'lat': lat, 'lon': lon,
            'cliente': str(c.cliente),
            'ciudad': c.ciudad or (str(c.ciudad_ref) if c.ciudad_ref_id else ''),
            'sector': c.sector_urbanizacion or '', 'direccion': c.direccion or '',
            'activo': (bool((c.fecha_inicio_original or c.fecha_inicio) <= fecha_consulta and (not c.fecha_fin_contrato or c.fecha_fin_contrato >= fecha_consulta)) if fecha_consulta else c.activo),
            'frecuencia': c.get_frecuencia_display() if c.frecuencia else '',
            'tecnico_designado': str(c.tecnico_designado) if c.tecnico_designado_id else 'Sin asignar',
        })
    return render(request, 'dashboard/mapa_expansion.html', {
        'maptiler_api_key': os.environ.get('MAPTILER_API_KEY', '').strip(),
        'puntos': puntos, 'pendientes': pendientes, 'modo': modo,
        'fecha_consulta': fecha_consulta.isoformat() if fecha_consulta else '',
        'ciudades': ciudades, 'ciudad_seleccionada': ciudad,
        'resueltos': resueltos, 'geocoding_habilitado': bool(api_key),
        'total_activos': Contrato.objects.filter(activo=True).count(),
        'total_historicos': Contrato.objects.filter(activo=False).count(),
        'ciudades_activas': Contrato.objects.filter(activo=True).exclude(ciudad='').values('ciudad').distinct().count(),
    })
