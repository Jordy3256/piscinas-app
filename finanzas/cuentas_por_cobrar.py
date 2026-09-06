from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from contratos.models import Contrato
from .models import Factura, FacturaItem, PromocionContrato


MESES = (
    (1, "Enero"), (2, "Febrero"), (3, "Marzo"), (4, "Abril"),
    (5, "Mayo"), (6, "Junio"), (7, "Julio"), (8, "Agosto"),
    (9, "Septiembre"), (10, "Octubre"), (11, "Noviembre"), (12, "Diciembre"),
)


def promocion_para_periodo(contrato, anio, mes):
    clave = int(anio) * 100 + int(mes)
    for promo in PromocionContrato.objects.filter(contrato=contrato, activa=True).order_by("-creada_en", "-id"):
        if promo.periodo_inicio_clave <= clave <= promo.periodo_fin_clave:
            return promo
    return None

def valores_promocion(contrato, anio, mes):
    base = Decimal(contrato.precio_mensual or 0).quantize(Decimal("0.01"))
    promo = promocion_para_periodo(contrato, anio, mes)
    if not promo:
        return {"promocion": None, "valor_contractual": base, "descuento": Decimal("0.00"), "total": base}
    datos = promo.calcular(base); datos["promocion"] = promo; return datos


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


def _desplazar_mes(anio, mes, desplazamiento):
    indice = (int(anio) * 12 + (int(mes) - 1)) + int(desplazamiento)
    return indice // 12, indice % 12 + 1


def cuotas_programadas_para_mes_cobro(contrato, anio_cobro, mes_cobro, meses_atras=12):
    """
    Devuelve únicamente las cuotas cuya FECHA REAL DE COBRO cae en el mes elegido.

    El periodo de servicio y el mes de cobro no son necesariamente iguales.
    Ejemplo:
      contrato inicia 05/09/2026
      cierre de periodo = 05/10/2026
      al generar SEPTIEMBRE no se crea esa cuenta;
      aparece al generar OCTUBRE.
    """
    resultado = []
    vistos = set()

    for desplazamiento in range(-meses_atras, 1):
        periodo_anio, periodo_mes = _desplazar_mes(anio_cobro, mes_cobro, desplazamiento)
        for cuota in contrato.calendario_cobros(periodo_anio, periodo_mes):
            fecha = cuota.get("fecha_cobro_desde") or cuota.get("fecha_vencimiento")
            if not fecha or fecha.year != int(anio_cobro) or fecha.month != int(mes_cobro):
                continue

            # No generar periodos que finalizaron antes de que el contrato exista.
            if contrato.fecha_inicio and cuota["periodo_fin"] <= contrato.fecha_inicio:
                continue

            clave = (periodo_anio, periodo_mes, cuota["cuota_numero"])
            if clave in vistos:
                continue
            vistos.add(clave)
            resultado.append((periodo_anio, periodo_mes, cuota))

    resultado.sort(
        key=lambda x: (
            x[2]["fecha_cobro_desde"],
            x[0],
            x[1],
            x[2]["cuota_numero"],
        )
    )
    return resultado


def previsualizar_facturas_periodo(anio, mes):
    contratos = list(contratos_facturables())
    nuevas_detalle = []
    existentes = 0
    previstas = 0
    valor_nuevo = Decimal("0.00")
    valor_total_periodo = Decimal("0.00")
    contratos_con_cobro = set()

    for contrato in contratos:
        promo_cache = {}
        for periodo_anio, periodo_mes, cuota in cuotas_programadas_para_mes_cobro(
            contrato, anio, mes
        ):
            previstas += 1
            contratos_con_cobro.add(contrato.pk)

            clave_periodo = (periodo_anio, periodo_mes)
            if clave_periodo not in promo_cache:
                promo_cache[clave_periodo] = valores_promocion(
                    contrato, periodo_anio, periodo_mes
                )
            promo_datos = promo_cache[clave_periodo]
            proporcion = (
                cuota["valor"] / Decimal(contrato.precio_mensual or 1)
                if contrato.precio_mensual
                else Decimal("0")
            )
            valor_cuota = (promo_datos["total"] * proporcion).quantize(Decimal("0.01"))
            valor_total_periodo += valor_cuota

            ya_existe = Factura.objects.filter(
                contrato=contrato,
                periodo_anio=periodo_anio,
                periodo_mes=periodo_mes,
                cuota_numero=cuota["cuota_numero"],
            ).exists()
            if ya_existe:
                existentes += 1
                continue

            valor_nuevo += valor_cuota
            nuevas_detalle.append({
                "contrato": contrato,
                "cliente": contrato.cliente,
                "periodo_anio": periodo_anio,
                "periodo_mes": periodo_mes,
                "periodo_inicio": cuota["periodo_inicio"],
                "periodo_fin": cuota["periodo_fin"],
                "cuota_numero": cuota["cuota_numero"],
                "total_cuotas": cuota["total_cuotas"],
                "fecha_cobro": cuota["fecha_cobro_desde"],
                "fecha_vencimiento": cuota["fecha_vencimiento"],
                "valor": valor_cuota,
                "promocion": promo_datos["promocion"],
            })

    return {
        "anio": anio,
        "mes": mes,
        "contratos_activos": len(contratos),
        "contratos_con_cobro": len(contratos_con_cobro),
        "obligaciones_previstas": previstas,
        "nuevas": len(nuevas_detalle),
        "existentes": existentes,
        "valor_nuevo": valor_nuevo,
        "valor_total_periodo": valor_total_periodo,
        "contratos_nuevos": nuevas_detalle,
    }


@transaction.atomic
def generar_factura_contrato(contrato, anio, mes, usuario=None):
    if not contrato.activo or not contrato.precio_mensual or contrato.precio_mensual <= 0:
        return [], 0

    creadas = []
    fecha_facturacion = contrato.fecha_programada_facturacion(anio, mes)
    promo_datos = valores_promocion(contrato, anio, mes)
    cuotas = contrato.calendario_cobros(anio, mes)
    for cuota in cuotas:
        proporcion = (cuota["valor"] / Decimal(contrato.precio_mensual or 1)) if contrato.precio_mensual else Decimal("0")
        valor_cuota = (promo_datos["total"] * proporcion).quantize(Decimal("0.01"))
        descuento_cuota = max(cuota["valor"] - valor_cuota, Decimal("0.00"))
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
                "subtotal": valor_cuota,
                "impuesto": Decimal("0.00"),
                "total": valor_cuota,
                "valor_contractual": cuota["valor"],
                "descuento_promocion": descuento_cuota,
                "promocion": promo_datos["promocion"],
                "promocion_nombre": promo_datos["promocion"].nombre if promo_datos["promocion"] else "",
                "estado": Factura.ESTADO_PROMOCION if valor_cuota == 0 and promo_datos["promocion"] else Factura.ESTADO_PENDIENTE,
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
                precio_unitario=valor_cuota,
            )
            creadas.append(factura)
    return creadas, len(creadas)


def generar_facturas_periodo(anio, mes, usuario=None):
    """
    Genera exclusivamente cuentas cuya fecha programada de cobro cae dentro
    del mes solicitado. El mes solicitado es MES DE COBRO, no mes de servicio.
    """
    creadas = 0
    existentes = 0
    errores = []
    valor_generado = Decimal("0.00")
    detalle_creadas = []

    for contrato in contratos_facturables():
        try:
            for periodo_anio, periodo_mes, cuota in cuotas_programadas_para_mes_cobro(
                contrato, anio, mes
            ):
                factura_existente = Factura.objects.filter(
                    contrato=contrato,
                    periodo_anio=periodo_anio,
                    periodo_mes=periodo_mes,
                    cuota_numero=cuota["cuota_numero"],
                ).first()
                if factura_existente:
                    existentes += 1
                    continue

                facturas, _ = generar_factura_contrato(
                    contrato, periodo_anio, periodo_mes, usuario=usuario
                )
                # generar_factura_contrato puede crear más de una cuota del mismo
                # periodo. Conservamos solamente como resultado del proceso las
                # que corresponden al mes de cobro solicitado; las otras no deben
                # existir todavía, por lo que se eliminan si fueron creadas aquí.
                for factura in facturas:
                    if factura.fecha_cobro_desde.year == int(anio) and factura.fecha_cobro_desde.month == int(mes):
                        creadas += 1
                        valor_generado += factura.total
                        detalle_creadas.append(factura)
                    else:
                        factura.delete()

        except Exception as exc:
            errores.append(f"Contrato {contrato.pk}: {exc}")

    return {
        "creadas": creadas,
        "existentes": existentes,
        "errores": errores,
        "valor_generado": valor_generado,
        "detalle_creadas": detalle_creadas,
    }

