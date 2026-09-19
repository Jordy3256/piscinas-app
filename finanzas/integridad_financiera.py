from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import Factura

CENTAVO = Decimal('0.01')
CERO = Decimal('0.00')


def _d(valor):
    return Decimal(valor or 0).quantize(CENTAVO)


def total_contractual_calendario(contrato, cuotas):
    return sum((_d(c.get('valor')) for c in cuotas), CERO).quantize(CENTAVO)


def total_contractual_esperado(contrato, cuotas):
    if not cuotas:
        return CERO
    meses = int(cuotas[0].get('meses_adelantados') or 1)
    return (_d(contrato.precio_mensual) * Decimal(meses)).quantize(CENTAVO)


def validar_calendario_cobros(contrato, cuotas, *, lanzar=True):
    """Invariante central: fraccionar un cobro nunca aumenta el contrato.

    Para un periodo mensual de $80, 1, 2, 3 o N cuotas deben sumar exactamente
    $80 de base contractual. En anticipos, el máximo es $80 x meses cubiertos.
    El IVA se calcula aparte y no altera esta base.
    """
    errores = []
    if not cuotas:
        return errores

    total_cuotas = int(cuotas[0].get('total_cuotas') or len(cuotas) or 1)
    numeros = [int(c.get('cuota_numero') or 0) for c in cuotas]
    if any(int(c.get('total_cuotas') or 0) != total_cuotas for c in cuotas):
        errores.append('Las cuotas del periodo no comparten el mismo total_cuotas.')
    if sorted(numeros) != list(range(1, len(cuotas) + 1)):
        errores.append('La numeración de cuotas del periodo no es consecutiva.')
    if total_cuotas != len(cuotas):
        errores.append(f'El periodo declara {total_cuotas} cuotas pero genera {len(cuotas)}.')

    esperado = total_contractual_esperado(contrato, cuotas)
    calculado = total_contractual_calendario(contrato, cuotas)
    if calculado != esperado:
        errores.append(
            f'El calendario suma ${calculado:.2f} pero el contrato permite ${esperado:.2f} de base contractual.'
        )

    if errores and lanzar:
        raise ValidationError(' '.join(errores))
    return errores


def esquema_historico_canonico(facturas):
    """Selecciona el esquema que nació primero para un periodo ya materializado.

    Evita que reportes mezclen una mensualidad histórica 1/1 con cuotas 2/2
    creadas posteriormente por un cambio de configuración.
    """
    activas = [f for f in facturas if f.estado != Factura.ESTADO_ANULADA]
    if not activas:
        return []
    primera = min(activas, key=lambda f: (f.creada_en, f.id))
    esquema = int(primera.total_cuotas or 1)
    return [f for f in activas if int(f.total_cuotas or 1) == esquema]


def auditar_integridad_facturas(queryset=None):
    """Auditoría solo lectura de importes/esquemas ya almacenados."""
    qs = queryset or Factura.objects.all()
    qs = qs.select_related('contrato', 'cliente').exclude(estado=Factura.ESTADO_ANULADA).order_by(
        'contrato_id', 'periodo_anio', 'periodo_mes', 'creada_en', 'id'
    )
    grupos = defaultdict(list)
    for f in qs:
        grupos[(f.contrato_id, f.periodo_anio, f.periodo_mes)].append(f)

    incidencias = []
    for clave, facturas in grupos.items():
        contrato = facturas[0].contrato
        esquemas = sorted({int(f.total_cuotas or 1) for f in facturas})
        canonicas = esquema_historico_canonico(facturas)
        suma_base = sum((_d(f.valor_contractual or f.subtotal) for f in canonicas), CERO)
        meses = max([int(getattr(f, 'meses_adelantados', 0) or 0) for f in []] or [1])
        esperado = _d(contrato.precio_mensual) * Decimal(meses)
        motivos = []
        if len(esquemas) > 1:
            motivos.append(f'esquemas incompatibles {esquemas}')
        # Para bloques adelantados una sola factura puede representar varios meses;
        # su periodo_fin permite distinguirlos sin asumir que es mensual.
        if canonicas:
            f0 = canonicas[0]
            if f0.periodo_inicio and f0.periodo_fin:
                meses_aprox = (f0.periodo_fin.year - f0.periodo_inicio.year) * 12 + (f0.periodo_fin.month - f0.periodo_inicio.month)
                if meses_aprox > 1 and len(canonicas) == 1:
                    esperado = _d(contrato.precio_mensual) * Decimal(meses_aprox)
        if suma_base != esperado:
            motivos.append(f'base canónica ${suma_base:.2f} vs contractual ${esperado:.2f}')
        if motivos:
            incidencias.append({
                'contrato_id': contrato.id,
                'cliente': str(facturas[0].cliente),
                'periodo': f'{clave[1]}-{clave[2]:02d}',
                'facturas': [f.id for f in facturas],
                'motivos': motivos,
            })
    return incidencias
