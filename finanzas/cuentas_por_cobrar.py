from calendar import monthrange
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from contratos.models import Contrato
from .models import Factura, FacturaItem


def fecha_vencimiento_contrato(contrato, anio, mes):
    ultimo = monthrange(anio, mes)[1]
    if contrato.forma_pago == "adelantado":
        dia = 1
    elif contrato.forma_pago == "fin_mensualidad":
        dia = ultimo
    else:
        dia = min(getattr(contrato.fecha_inicio, "day", 5) or 5, ultimo)
    return date(anio, mes, dia)


@transaction.atomic
def generar_factura_contrato(contrato, anio, mes, usuario=None):
    if not contrato.activo:
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
    contratos = Contrato.objects.select_related("cliente").filter(activo=True)
    for contrato in contratos:
        try:
            _, creada = generar_factura_contrato(contrato, anio, mes, usuario=usuario)
            if creada:
                creadas += 1
            else:
                existentes += 1
        except Exception as exc:
            errores.append(f"Contrato {contrato.pk}: {exc}")
    return {"creadas": creadas, "existentes": existentes, "errores": errores}
