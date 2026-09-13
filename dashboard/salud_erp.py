from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from clientes.models import Cliente
from contratos.models import Contrato
from finanzas.models import Factura, ObligacionTrabajador
from inventario.models import Insumo, InventarioContrato
from mantenimientos.models import Mantenimiento

try:
    from finanzas.models import AvisoFacturacion
except Exception:
    AvisoFacturacion = None


def _item(*, clave, severidad, titulo, cantidad, descripcion, url, accion):
    return {
        "clave": clave,
        "severidad": severidad,
        "titulo": titulo,
        "cantidad": int(cantidad or 0),
        "descripcion": descripcion,
        "url": url,
        "accion": accion,
    }


def diagnosticar_salud_erp(*, hoy=None):
    """
    Diagnóstico de consistencia operativa del ERP.

    Solo devuelve incidencias accionables. No modifica información.
    severidad:
      - critica: puede afectar servicio, cobro o pago.
      - atencion: conviene corregir pronto.
      - aviso: dato incompleto o prevención.
    """
    hoy = hoy or timezone.localdate()
    proximos_14 = hoy + timedelta(days=14)
    items = []

    contratos_activos = Contrato.objects.filter(activo=True)

    # Contratos sin técnico en programación automática.
    qs = contratos_activos.filter(
        generacion_automatica=True,
        tecnico_designado__isnull=True,
    )
    if qs.exists():
        items.append(_item(
            clave="contratos_sin_tecnico",
            severidad="critica",
            titulo="Contratos automáticos sin técnico",
            cantidad=qs.count(),
            descripcion="No pueden asignar correctamente los mantenimientos futuros.",
            url="/dashboard/contratos/",
            accion="Revisar contratos",
        ))

    # Configuración comercial incompleta.
    qs = contratos_activos.filter(
        Q(precio_mensual__lte=0) | Q(frecuencia="") | Q(forma_pago="")
    )
    if qs.exists():
        items.append(_item(
            clave="contratos_incompletos",
            severidad="critica",
            titulo="Contratos con datos comerciales incompletos",
            cantidad=qs.count(),
            descripcion="Falta precio, frecuencia o forma de pago.",
            url="/dashboard/contratos/",
            accion="Completar contratos",
        ))

    # Contratos vencidos que continúan administrativamente activos.
    qs = contratos_activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__lt=hoy,
    )
    if qs.exists():
        items.append(_item(
            clave="contratos_vencidos",
            severidad="critica",
            titulo="Contratos vencidos pendientes de decisión",
            cantidad=qs.count(),
            descripcion="El sistema ya detiene nuevos ciclos, pero debes renovar o finalizar estos contratos.",
            url="/dashboard/contratos/",
            accion="Revisar vencidos",
        ))

    # Contratos por vencer.
    por_vencer = 0
    for contrato in contratos_activos.filter(
        fecha_fin_contrato__isnull=False,
        fecha_fin_contrato__gte=hoy,
    ).only("fecha_fin_contrato", "aviso_vencimiento_dias"):
        if contrato.fecha_fin_contrato <= hoy + timedelta(days=int(contrato.aviso_vencimiento_dias or 30)):
            por_vencer += 1
    if por_vencer:
        items.append(_item(
            clave="contratos_por_vencer",
            severidad="atencion",
            titulo="Contratos próximos a vencer",
            cantidad=por_vencer,
            descripcion="Conviene gestionar la renovación antes de que termine la vigencia.",
            url="/dashboard/contratos/",
            accion="Planificar renovaciones",
        ))

    # Contratos automáticos sin ninguna visita pendiente en los próximos 14 días.
    contratos_programables = contratos_activos.filter(
        generacion_automatica=True,
        tecnico_designado__isnull=False,
    ).exclude(frecuencia="personalizado")
    sin_programacion = 0
    for contrato in contratos_programables.only("id", "fecha_fin_contrato"):
        if contrato.fecha_fin_contrato and contrato.fecha_fin_contrato < hoy:
            continue
        existe = Mantenimiento.objects.filter(
            contrato=contrato,
            estado="pendiente",
            fecha__range=(hoy, proximos_14),
        ).exists()
        if not existe:
            sin_programacion += 1
    if sin_programacion:
        items.append(_item(
            clave="contratos_sin_programacion",
            severidad="critica",
            titulo="Contratos sin visitas futuras",
            cantidad=sin_programacion,
            descripcion="Contratos automáticos sin mantenimiento pendiente dentro de los próximos 14 días.",
            url="/dashboard/operativo/",
            accion="Revisar programación",
        ))

    # Mantenimientos atrasados.
    qs = Mantenimiento.objects.filter(estado="pendiente", fecha__lt=hoy)
    if qs.exists():
        items.append(_item(
            clave="mantenimientos_atrasados",
            severidad="critica",
            titulo="Mantenimientos atrasados",
            cantidad=qs.count(),
            descripcion="Visitas que debían realizarse antes de hoy y continúan pendientes.",
            url="/dashboard/operativo/",
            accion="Resolver agenda",
        ))

    # Cartera vencida.
    facturas_vencidas = [
        f for f in Factura.objects.exclude(
            estado__in=[Factura.ESTADO_PAGADA, Factura.ESTADO_ANULADA, Factura.ESTADO_PROMOCION]
        ).filter(fecha_vencimiento__lt=hoy).prefetch_related("pagos")
        if f.saldo > 0
    ]
    if facturas_vencidas:
        items.append(_item(
            clave="cartera_vencida",
            severidad="critica",
            titulo="Cuentas por cobrar vencidas",
            cantidad=len(facturas_vencidas),
            descripcion="Existen saldos vencidos que requieren gestión de cobranza.",
            url="/dashboard/finanzas/cartera/",
            accion="Abrir Cartera",
        ))

    # Nómina vencida.
    obligaciones_vencidas = [
        o for o in ObligacionTrabajador.objects.exclude(
            estado__in=[ObligacionTrabajador.ESTADO_PAGADO, ObligacionTrabajador.ESTADO_ANULADO]
        ).filter(fecha_pago_programada__lt=hoy).prefetch_related("pagos")
        if o.saldo > 0
    ]
    if obligaciones_vencidas:
        items.append(_item(
            clave="nomina_vencida",
            severidad="critica",
            titulo="Nómina vencida",
            cantidad=len(obligaciones_vencidas),
            descripcion="Pagos a trabajadores con fecha programada anterior a hoy.",
            url="/dashboard/finanzas/nomina/",
            accion="Revisar Nómina",
        ))

    # Productos generales en nivel crítico.
    qs = Insumo.objects.filter(
        activo=True,
        controla_inventario=True,
        stock__lte=0,
    )
    agotados = qs.count()
    bajos = 0
    for insumo in Insumo.objects.filter(activo=True, controla_inventario=True).only("stock", "stock_minimo"):
        if Decimal(insumo.stock or 0) > 0 and Decimal(insumo.stock or 0) <= Decimal(insumo.stock_minimo or 0):
            bajos += 1

    if agotados:
        items.append(_item(
            clave="inventario_agotado",
            severidad="critica",
            titulo="Productos agotados",
            cantidad=agotados,
            descripcion="Productos activos con inventario general en cero.",
            url="/dashboard/inventario/",
            accion="Reponer stock",
        ))
    if bajos:
        items.append(_item(
            clave="inventario_bajo",
            severidad="atencion",
            titulo="Productos con stock bajo",
            cantidad=bajos,
            descripcion="Productos por debajo o en su nivel mínimo definido.",
            url="/dashboard/inventario/",
            accion="Revisar inventario",
        ))

    # Inventario en sitio crítico.
    criticos_sitio = 0
    for inv in InventarioContrato.objects.select_related("contrato", "insumo").filter(contrato__activo=True):
        if inv.estado_stock in {"agotado", "critico"}:
            criticos_sitio += 1
    if criticos_sitio:
        items.append(_item(
            clave="inventario_sitio_critico",
            severidad="atencion",
            titulo="Inventario en sitio crítico",
            cantidad=criticos_sitio,
            descripcion="Existencias de contratos que necesitan reposición o verificación.",
            url="/dashboard/inventario/",
            accion="Planificar reposición",
        ))

    # Clientes activos sin ubicación suficiente.
    qs = Cliente.objects.filter(activo=True).filter(
        Q(ciudad_ref__isnull=True) | Q(direccion__exact="")
    )
    if qs.exists():
        items.append(_item(
            clave="clientes_ubicacion_incompleta",
            severidad="aviso",
            titulo="Clientes con ubicación incompleta",
            cantidad=qs.count(),
            descripcion="Falta ciudad normalizada o dirección, lo que puede afectar rutas y filtros.",
            url="/dashboard/clientes/",
            accion="Completar datos",
        ))

    # Facturación externa pendiente (si el modelo existe).
    if AvisoFacturacion is not None:
        try:
            pendientes = AvisoFacturacion.objects.filter(
                estado=AvisoFacturacion.ESTADO_PENDIENTE,
                fecha_programada__lte=hoy,
            ).count()
            if pendientes:
                items.append(_item(
                    clave="facturacion_pendiente",
                    severidad="atencion",
                    titulo="Facturas externas por realizar",
                    cantidad=pendientes,
                    descripcion="Avisos de facturación cuya fecha programada ya llegó.",
                    url="/dashboard/finanzas/facturacion/",
                    accion="Revisar facturación",
                ))
        except Exception:
            pass

    orden = {"critica": 0, "atencion": 1, "aviso": 2}
    items.sort(key=lambda x: (orden.get(x["severidad"], 9), -x["cantidad"], x["titulo"]))

    criticas = sum(1 for x in items if x["severidad"] == "critica")
    atencion = sum(1 for x in items if x["severidad"] == "atencion")
    avisos = sum(1 for x in items if x["severidad"] == "aviso")
    total_afectados = sum(x["cantidad"] for x in items)

    if criticas:
        estado = "critico"
        etiqueta = "Requiere atención"
    elif atencion:
        estado = "atencion"
        etiqueta = "Hay puntos por revisar"
    elif avisos:
        estado = "aviso"
        etiqueta = "Salud estable con avisos"
    else:
        estado = "saludable"
        etiqueta = "Todo en orden"

    return {
        "fecha": hoy,
        "estado": estado,
        "etiqueta": etiqueta,
        "items": items,
        "total_items": len(items),
        "total_afectados": total_afectados,
        "criticas": criticas,
        "atencion": atencion,
        "avisos": avisos,
    }
