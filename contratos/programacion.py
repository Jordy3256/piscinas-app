from calendar import monthrange
from datetime import date, timedelta

from django.db import transaction
from django.utils import timezone

from mantenimientos.models import Mantenimiento


DIAS_SEMANA = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

FRECUENCIA_CANTIDAD_DIAS = {
    "1_semanal": 1,
    "2_semanales": 2,
    "3_semanales": 3,
    "quincenal": 1,
}


def sumar_un_mes(fecha_base: date) -> date:
    """Devuelve la misma fecha del mes siguiente, ajustando meses cortos."""
    mes = fecha_base.month + 1
    anio = fecha_base.year
    if mes > 12:
        mes = 1
        anio += 1
    dia = min(fecha_base.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def normalizar_dias(dias):
    resultado = []
    for valor in dias or []:
        try:
            numero = int(valor)
        except (TypeError, ValueError):
            continue
        if 0 <= numero <= 6 and numero not in resultado:
            resultado.append(numero)
    return sorted(resultado)


def validar_programacion(frecuencia, dias, trabajador, automatica=True):
    errores = []
    dias = normalizar_dias(dias)

    if automatica and trabajador is None:
        errores.append("Debes seleccionar un técnico designado para la programación automática.")

    if frecuencia == "personalizado":
        if automatica:
            errores.append(
                "La frecuencia personalizada no puede generar mantenimientos automáticamente. "
                "Desactiva la programación automática o selecciona una frecuencia estándar."
            )
        return errores

    cantidad = FRECUENCIA_CANTIDAD_DIAS.get(frecuencia)
    if automatica and cantidad is not None and len(dias) != cantidad:
        etiqueta = "día" if cantidad == 1 else "días"
        errores.append(
            f"Para esta frecuencia debes seleccionar exactamente {cantidad} {etiqueta} de visita."
        )

    return errores


def _fechas_semanales(inicio, fin, dias):
    actual = inicio
    dias = set(normalizar_dias(dias))
    while actual <= fin:
        if actual.weekday() in dias:
            yield actual
        actual += timedelta(days=1)


def _fecha_quincenal_inicial(fecha_inicio_contrato, dia_objetivo):
    """
    Ancla la primera visita quincenal al inicio REAL del contrato.

    La referencia es dos semanas después de la fecha de inicio y se ajusta al
    día de visita seleccionado más cercano. A partir de esa fecha la cadencia
    permanece fija cada 14 días, evitando que cambie al entrar al ERP otro día.
    """
    referencia = fecha_inicio_contrato + timedelta(days=14)

    hacia_adelante = (dia_objetivo - referencia.weekday()) % 7
    fecha_adelante = referencia + timedelta(days=hacia_adelante)
    fecha_atras = fecha_adelante - timedelta(days=7)

    distancia_adelante = abs((fecha_adelante - referencia).days)
    distancia_atras = abs((referencia - fecha_atras).days)

    if distancia_atras < distancia_adelante and fecha_atras > fecha_inicio_contrato:
        return fecha_atras
    return fecha_adelante


def _fechas_quincenales(inicio, fin, dias, fecha_inicio_contrato=None):
    dias = normalizar_dias(dias)
    if not dias:
        return

    dia_objetivo = dias[0]
    ancla_contrato = fecha_inicio_contrato or inicio
    primera = _fecha_quincenal_inicial(ancla_contrato, dia_objetivo)

    # Si estamos extendiendo una programación ya existente, avanzamos desde el
    # ancla original sin reiniciar la quincena desde "hoy".
    if primera < inicio:
        diferencia = (inicio - primera).days
        saltos = (diferencia + 13) // 14
        primera += timedelta(days=saltos * 14)

    actual = primera
    while actual <= fin:
        yield actual
        actual += timedelta(days=14)


def fechas_programadas(contrato, inicio, fin):
    if contrato.frecuencia == "quincenal":
        return list(
            _fechas_quincenales(
                inicio,
                fin,
                contrato.dias_visita,
                fecha_inicio_contrato=contrato.fecha_inicio,
            )
        )
    if contrato.frecuencia in {"1_semanal", "2_semanales", "3_semanales"}:
        return list(_fechas_semanales(inicio, fin, contrato.dias_visita))
    return []


@transaction.atomic
def generar_mantenimientos_contrato(contrato, desde=None, hasta=None, reconciliar=False):
    """
    Genera visitas sin duplicados y asigna el técnico del contrato.

    Si reconciliar=True, elimina solo visitas futuras, pendientes y automáticas
    antes de reconstruirlas. Nunca toca mantenimientos realizados ni manuales.
    """
    hoy = timezone.localdate()

    if not contrato.activo or not contrato.generacion_automatica:
        return {"creados": 0, "existentes": 0, "eliminados": 0, "hasta": None}

    errores = validar_programacion(
        contrato.frecuencia,
        contrato.dias_visita,
        contrato.tecnico_designado,
        automatica=True,
    )
    if errores:
        return {
            "creados": 0,
            "existentes": 0,
            "eliminados": 0,
            "hasta": None,
            "errores": errores,
        }

    inicio = desde or max(contrato.fecha_inicio, hoy)
    fin = hasta or sumar_un_mes(inicio)

    eliminados = 0
    if reconciliar:
        eliminados, _ = Mantenimiento.objects.filter(
            contrato=contrato,
            fecha__gte=inicio,
            estado="pendiente",
            automatico=True,
        ).delete()

    creados = 0
    existentes = 0
    for fecha_visita in fechas_programadas(contrato, inicio, fin):
        mantenimiento, fue_creado = Mantenimiento.objects.get_or_create(
            contrato=contrato,
            fecha=fecha_visita,
            defaults={
                "cliente": contrato.cliente,
                "estado": "pendiente",
                "automatico": True,
            },
        )
        if fue_creado:
            creados += 1
        else:
            existentes += 1
            cambios = []
            if mantenimiento.cliente_id != contrato.cliente_id:
                mantenimiento.cliente = contrato.cliente
                cambios.append("cliente")
            if mantenimiento.automatico and mantenimiento.estado == "pendiente" and cambios:
                mantenimiento.save(update_fields=cambios)

        if mantenimiento.estado == "pendiente" and contrato.tecnico_designado_id:
            mantenimiento.trabajadores.set([contrato.tecnico_designado])

    contrato.programado_hasta = fin
    contrato.save(update_fields=["programado_hasta"])

    return {
        "creados": creados,
        "existentes": existentes,
        "eliminados": eliminados,
        "hasta": fin,
        "errores": [],
    }


@transaction.atomic
def cancelar_programacion_futura(contrato, desde=None):
    inicio = desde or timezone.localdate()
    eliminados, _ = Mantenimiento.objects.filter(
        contrato=contrato,
        fecha__gte=inicio,
        estado="pendiente",
        automatico=True,
    ).delete()
    contrato.programado_hasta = None
    contrato.save(update_fields=["programado_hasta"])
    return eliminados


def mantener_programacion_automatica(horizonte_dias=14):
    """Mantiene un mes futuro de visitas para todos los contratos automáticos activos.

    Se ejecuta al entrar al ERP. Si un contrato está sin programación o entra
    dentro del horizonte de renovación, agrega el siguiente bloque sin tocar
    visitas realizadas ni crear duplicados.
    """
    from contratos.models import Contrato

    hoy = timezone.localdate()
    limite = hoy + timedelta(days=horizonte_dias)
    contratos = (
        Contrato.objects
        .filter(activo=True, generacion_automatica=True)
        .select_related("tecnico_designado", "cliente")
        .order_by("id")
    )

    renovados = 0
    creados = 0
    errores = []
    for contrato in contratos:
        if contrato.programado_hasta and contrato.programado_hasta > limite:
            continue

        desde = (
            contrato.programado_hasta + timedelta(days=1)
            if contrato.programado_hasta and contrato.programado_hasta >= hoy
            else max(contrato.fecha_inicio, hoy)
        )
        hasta = sumar_un_mes(desde)
        resultado = generar_mantenimientos_contrato(
            contrato,
            desde=desde,
            hasta=hasta,
            reconciliar=False,
        )
        if resultado.get("errores"):
            errores.append({"contrato": contrato.pk, "errores": resultado["errores"]})
            continue
        renovados += 1
        creados += resultado.get("creados", 0)

    return {"renovados": renovados, "creados": creados, "errores": errores}
