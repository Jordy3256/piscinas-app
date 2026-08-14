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


def fecha_vencimiento_contrato(contrato, anio, mes, cuota_numero=1):
    calendario = contrato.calendario_cobros(anio, mes)
    indice = min(max(int(cuota_numero or 1), 1), len(calendario)) - 1
    return calendario[indice]["fecha_vencimiento"]


def contratos_facturables():
    return (
        Contrato.objects.select_related("cliente")
        .filter(activo=True, precio_mensual__gt=0)
        .order_by("cliente__nombre", "pk")
    )


def previsualizar_facturas_periodo(anio, mes):
    contratos = list(contratos_facturables())
    existentes = set(
        Factura.objects.filter(
            contrato_id__in=[c.pk for c in contratos],
            periodo_anio=anio,
            periodo_mes=mes,
        ).values_list("contrato_id", "cuota_numero")
    )
    nuevas = []
    valor_nuevo = Decimal("0.00")
    total_obligaciones = 0
    for contrato in contratos:
        for cuota in contrato.calendario_cobros(anio, mes):
            total_obligaciones += 1
            clave = (contrato.pk, cuota["cuota_numero"])
            if clave not in existentes:
                nuevas.append((contrato, cuota))
                valor_nuevo += cuota["valor"]
    return {
        "anio": anio,
        "mes": mes,
        "contratos_activos": len(contratos),
        "obligaciones_previstas": total_obligaciones,
        "nuevas": len(nuevas),
        "existentes": len(existentes),
        "valor_nuevo": valor_nuevo,
        "valor_total_periodo": sum((c.precio_mensual or Decimal("0.00") for c in contratos), Decimal("0.00")),
        "contratos_nuevos": nuevas,
    }


@transaction.atomic
def generar_factura_contrato(contrato, anio, mes, usuario=None):
    if not contrato.activo or not contrato.precio_mensual or contrato.precio_mensual <= 0:
        return [], 0

    creadas = []
    fecha_facturacion = contrato.fecha_programada_facturacion(anio, mes)
    for cuota in contrato.calendario_cobros(anio, mes):
        factura, creada = Factura.objects.get_or_create(
            contrato=contrato,
            periodo_anio=anio,
            periodo_mes=mes,
            cuota_numero=cuota["cuota_numero"],
            defaults={
                "cliente": contrato.cliente,
                "periodo_inicio": cuota["periodo_inicio"],
                "periodo_fin": cuota["periodo_fin"],
                "total_cuotas": cuota["total_cuotas"],
                "fecha_emision": timezone.localdate(),
                "fecha_cobro_desde": cuota["fecha_cobro_desde"],
                "fecha_vencimiento": cuota["fecha_vencimiento"],
                "fecha_facturacion_programada": fecha_facturacion,
                "requiere_factura": contrato.requiere_factura,
                "subtotal": cuota["valor"],
                "impuesto": Decimal("0.00"),
                "total": cuota["valor"],
                "observaciones": "Cuenta por cobrar generada automáticamente desde el calendario comercial del contrato.",
            },
        )
        if creada:
            descripcion = f"Servicio de mantenimiento {cuota['periodo_inicio']:%d/%m/%Y} al {cuota['periodo_fin']:%d/%m/%Y}"
            if cuota["total_cuotas"] > 1:
                descripcion += f" · cuota {cuota['cuota_numero']}/{cuota['total_cuotas']}"
            FacturaItem.objects.create(
                factura=factura,
                descripcion=descripcion,
                cantidad=Decimal("1.00"),
                precio_unitario=cuota["valor"],
            )
            creadas.append(factura)
    return creadas, len(creadas)


def generar_facturas_periodo(anio, mes, usuario=None):
    creadas = 0
    existentes = 0
    errores = []
    valor_generado = Decimal("0.00")
    for contrato in contratos_facturables():
        try:
            previstas = len(contrato.calendario_cobros(anio, mes))
            facturas, cantidad = generar_factura_contrato(contrato, anio, mes, usuario=usuario)
            creadas += cantidad
            existentes += previstas - cantidad
            valor_generado += sum((f.total for f in facturas), Decimal("0.00"))
        except Exception as exc:
            errores.append(f"Contrato {contrato.pk}: {exc}")
    return {"creadas": creadas, "existentes": existentes, "errores": errores, "valor_generado": valor_generado}
