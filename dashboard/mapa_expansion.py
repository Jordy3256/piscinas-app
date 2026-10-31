"""Mapa administrativo de piscinas; reutiliza el geocodificador de rutas.

No modifica enlaces, direcciones ni coordenadas previamente almacenadas.
"""
import logging
import os
from datetime import date

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone

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
    vista = request.GET.get('vista', 'vigentes')
    if vista not in ('vigentes', 'acumulados'):
        vista = 'vigentes'
    def parse_fecha(nombre):
        try:
            raw = (request.GET.get(nombre) or '').strip()
            return date.fromisoformat(raw) if raw else None
        except ValueError:
            return None

    fechas = [f for f in (parse_fecha('fecha'), parse_fecha('comparar'), parse_fecha('tercera')) if f]
    # Tres momentos cronológicos, sin duplicados; se conserva compatibilidad A/B.
    fechas = sorted(set(fechas))[:3]
    fecha_consulta = fechas[0] if fechas else None
    fecha_comparar = fechas[1] if len(fechas) > 1 else None
    fecha_tercera = fechas[2] if len(fechas) > 2 else None

    qs = (Contrato.objects.select_related('cliente', 'ciudad_ref', 'tecnico_designado')
          .prefetch_related('reactivaciones').order_by('id'))
    if fechas:
        # Cargar los contratos que comenzaron hasta el último corte; el estado
        # histórico se calcula abajo utilizando bajas y reactivaciones registradas.
        ultimo = fechas[-1]
        qs = qs.filter(Q(fecha_inicio_original__lte=ultimo) |
                       Q(fecha_inicio_original__isnull=True, fecha_inicio__lte=ultimo))
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
    comparacion_resumen = {'a': 0, 'b': 0, 'c': 0, 'altas': 0, 'bajas': 0, 'continuan': 0}
    resumen_pares = {'ab': {'altas': 0, 'bajas': 0}, 'bc': {'altas': 0, 'bajas': 0}}
    resumen_global = {'altas': 0, 'bajas': 0}

    def vigente_en_fecha(contrato, corte):
        # En el día actual el estado administrativo es la fuente de verdad.
        # La reconstrucción histórica por fechas puede considerar vigentes
        # contratos desactivados sin una fecha de baja registrada.
        if not corte or corte == timezone.localdate():
            return bool(contrato.activo)
        inicio = contrato.fecha_inicio_original or contrato.fecha_inicio
        if not inicio or corte < inicio:
            return False
        reactivaciones = sorted(contrato.reactivaciones.all(), key=lambda r: (r.fecha_reactivacion, r.pk))
        comienzo = inicio
        for reactivacion in reactivaciones:
            baja = reactivacion.fecha_baja_anterior
            if comienzo <= corte < reactivacion.fecha_reactivacion:
                return baja is None or corte < baja
            comienzo = reactivacion.fecha_reactivacion
        if corte < comienzo:
            return False
        if contrato.fecha_baja and corte >= contrato.fecha_baja:
            return False
        # La fecha fin se refiere al ciclo contractual actual, no a ciclos previos.
        if contrato.fecha_fin_contrato and corte > contrato.fecha_fin_contrato:
            return False
        return True

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
        estados = [vigente_en_fecha(c, f) for f in fechas]
        if fechas and vista == 'acumulados':
            inicio_real = c.fecha_inicio_original or c.fecha_inicio
            estados = [bool(inicio_real and inicio_real <= f) for f in fechas]
        vigente_a = estados[0] if estados else bool(c.activo)
        vigente_b = estados[1] if len(estados) > 1 else False
        vigente_c = estados[2] if len(estados) > 2 else False
        activo_fecha = vigente_a
        for i, clave in enumerate(('a', 'b', 'c')):
            if i < len(estados):
                comparacion_resumen[clave] += int(estados[i])
        if len(estados) >= 2:
            comparacion_resumen['altas'] += int(not estados[0] and estados[1])
            comparacion_resumen['bajas'] += int(estados[0] and not estados[1])
            comparacion_resumen['continuan'] += int(estados[0] and estados[1])
            resumen_global['altas'] += int(not estados[0] and estados[-1])
            resumen_global['bajas'] += int(estados[0] and not estados[-1])
            for key, i, j in (('ab', 0, 1), ('bc', 1, 2)):
                if j < len(estados):
                    resumen_pares[key]['altas'] += int(not estados[i] and estados[j])
                    resumen_pares[key]['bajas'] += int(estados[i] and not estados[j])
        estado_comparacion = ('continua' if vigente_a and vigente_b else 'alta' if vigente_b else 'baja') if len(estados) > 1 else ''
        puntos.append({
            'id': c.pk, 'lat': lat, 'lon': lon,
            'cliente': str(c.cliente),
            'ciudad': c.ciudad or (str(c.ciudad_ref) if c.ciudad_ref_id else ''),
            'sector': c.sector_urbanizacion or '', 'direccion': c.direccion or '',
            'activo': activo_fecha, 'vigente_a': vigente_a, 'vigente_b': vigente_b, 'vigente_c': vigente_c,
            'comparacion': estado_comparacion,
            'frecuencia': c.get_frecuencia_display() if c.frecuencia else '',
            'tecnico_designado': str(c.tecnico_designado) if c.tecnico_designado_id else 'Sin asignar',
        })
    return render(request, 'dashboard/mapa_expansion.html', {
        'maptiler_api_key': os.environ.get('MAPTILER_API_KEY', '').strip(),
        'puntos': puntos, 'pendientes': pendientes, 'modo': modo,
        'ciudades': ciudades, 'ciudad_seleccionada': ciudad,
        'fecha_consulta': fecha_consulta.isoformat() if fecha_consulta else '',
        'fecha_comparar': fecha_comparar.isoformat() if fecha_comparar else '',
        'fecha_tercera': fecha_tercera.isoformat() if fecha_tercera else '',
        'vista': vista, 'resumen_pares': resumen_pares, 'resumen_global': resumen_global,
        'resueltos': resueltos, 'geocoding_habilitado': bool(api_key),
        'comparacion_resumen': comparacion_resumen,
        'total_activos': Contrato.objects.filter(activo=True).count(),
        'total_historicos': Contrato.objects.filter(activo=False).count(),
        'ciudades_activas': Contrato.objects.filter(activo=True).exclude(ciudad='').values('ciudad').distinct().count(),
    })
