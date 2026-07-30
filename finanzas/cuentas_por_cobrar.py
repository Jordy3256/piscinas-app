from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from contratos.models import Contrato
from .models import Factura, FacturaItem


MESES = (
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
)


def fecha_vencimiento_contrato(contrato, anio, mes):
    ultimo = monthrange(anio, mes)[1]
    if contrato.forma_pago == "adelantado":
        dia = 1
    elif contrato.forma_pago == "fin_mensualidad":
        dia = ultimo
    elif contrato.forma_pago == "dia_fijo" and contrato.dia_pago:
        dia = min(max(int(contrato.dia_pago), 1), ultimo)
    else:
        dia = min(getattr(contrato.fecha_inicio, "day", 5) or 5, ultimo)
    return date(anio, mes, dia)


def contratos_facturables():
    """Contratos activos con cliente y un valor mensual válido."""
    return (
        Contrato.objects.select_related("cliente")
        .filter(activo=True, precio_mensual__gt=0)
        .order_by("cliente__nombre", "pk")
    )


def previsualizar_facturas_periodo(anio, mes):
    """Calcula lo que ocurriría sin escribir datos en la base."""
    contratos = list(contratos_facturables())
    ids = [contrato.pk for contrato in contratos]
    existentes_ids = set(
        Factura.objects.filter(
            contrato_id__in=ids,
            periodo_anio=anio,
            periodo_mes=mes,
        ).values_list("contrato_id", flat=True)
    )
    nuevos = [contrato for contrato in contratos if contrato.pk not in existentes_ids]
    valor_nuevo = sum((contrato.precio_mensual or Decimal("0.00") for contrato in nuevos), Decimal("0.00"))
    valor_total_periodo = sum((contrato.precio_mensual or Decimal("0.00") for contrato in contratos), Decimal("0.00"))
    return {
        "anio": anio,
        "mes": mes,
        "contratos_activos": len(contratos),
        "nuevas": len(nuevos),
        "existentes": len(existentes_ids),
        "valor_nuevo": valor_nuevo,
        "valor_total_periodo": valor_total_periodo,
        "contratos_nuevos": nuevos,
    }


@transaction.atomic
def generar_factura_contrato(contrato, anio, mes, usuario=None):
    if not contrato.activo or not contrato.precio_mensual or contrato.precio_mensual <= 0:
        return None, False
    factura, creada = Factura.objects.get_or_create(
        contrato=contrato,
        periodo_anio=anio,
        periodo_mes=mes,
        defaults={
            "cliente": contrato.cliente,
            "fecha_emision": timezone.localdate(),
            "fecha_vencimiento": fecha_vencimiento_contrato(contrato, anio, mes),
            "subtotal": contrato.precio_mensual,
            "impuesto": Decimal("0.00"),
            "total": contrato.precio_mensual,
            "observaciones": "Mensualidad generada automáticamente desde el contrato.",
        },
    )
    if creada:
        FacturaItem.objects.create(
            factura=factura,
            descripcion=f"Servicio de mantenimiento mensual - {factura.periodo_label}",
            cantidad=Decimal("1.00"),
            precio_unitario=contrato.precio_mensual,
        )
    return factura, creada


def generar_facturas_periodo(anio, mes, usuario=None):
    creadas = 0
    existentes = 0
    errores = []
    valor_generado = Decimal("0.00")
    contratos = contratos_facturables()
    for contrato in contratos:
        try:
            _, creada = generar_factura_contrato(contrato, anio, mes, usuario=usuario)
            if creada:
                creadas += 1
                valor_generado += contrato.precio_mensual or Decimal("0.00")
            else:
                existentes += 1
        except Exception as exc:
            errores.append(f"Contrato {contrato.pk}: {exc}")
    return {
        "creadas": creadas,
        "existentes": existentes,
        "errores": errores,
        "valor_generado": valor_generado,
    }
