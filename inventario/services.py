from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction

from .models import InventarioTrabajador, InventarioContrato, MovimientoInventario, PresentacionInsumo

Q3 = Decimal("0.001")
Q2 = Decimal("0.01")


def decimal_positivo(valor, nombre="Cantidad"):
    try:
        resultado = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{nombre} inválida.")
    if resultado <= 0:
        raise ValueError(f"{nombre} debe ser mayor a cero.")
    return resultado


def convertir_a_base(insumo, cantidad, unidad="base", presentacion=None):
    cantidad = decimal_positivo(cantidad)
    unidad = (unidad or "base").lower()

    if presentacion:
        if isinstance(presentacion, (str, int)):
            presentacion = PresentacionInsumo.objects.get(pk=presentacion, insumo=insumo, activa=True)
        return (cantidad * Decimal(presentacion.cantidad_base)).quantize(Q3, rounding=ROUND_HALF_UP)

    if insumo.unidad_base == "kg":
        if unidad in ("g", "gramo", "gramos"):
            return (cantidad / Decimal("1000")).quantize(Q3, rounding=ROUND_HALF_UP)
        if unidad in ("kg", "base", "kilogramo", "kilogramos"):
            return cantidad.quantize(Q3, rounding=ROUND_HALF_UP)
        raise ValueError("Para este producto utiliza gramos o kilogramos.")

    if insumo.unidad_base == "l":
        if unidad in ("ml", "mililitro", "mililitros"):
            return (cantidad / Decimal("1000")).quantize(Q3, rounding=ROUND_HALF_UP)
        if unidad in ("l", "lt", "litro", "litros", "base"):
            return cantidad.quantize(Q3, rounding=ROUND_HALF_UP)
        raise ValueError("Para este producto utiliza mililitros o litros.")

    raise ValueError("La unidad base del producto no es válida. Usa kg o L.")


def _costo_total(insumo, cantidad_base):
    return (Decimal(insumo.costo or 0) * Decimal(cantidad_base)).quantize(Q2, rounding=ROUND_HALF_UP)


@transaction.atomic
def entregar_a_trabajador(*, insumo, trabajador, cantidad_base, usuario=None, observacion=""):
    insumo = insumo.__class__.objects.select_for_update().get(pk=insumo.pk)
    cantidad_base = decimal_positivo(cantidad_base)
    if Decimal(insumo.stock) < cantidad_base:
        raise ValueError(f"Stock general insuficiente. Disponible: {insumo.stock} {insumo.unidad_corta}.")

    inv, _ = InventarioTrabajador.objects.select_for_update().get_or_create(trabajador=trabajador, insumo=insumo)
    general_antes = Decimal(insumo.stock)
    trabajador_antes = Decimal(inv.stock)
    insumo.stock = general_antes - cantidad_base
    inv.stock = trabajador_antes + cantidad_base
    insumo.save(update_fields=["stock"])
    inv.save(update_fields=["stock", "actualizado_en"])

    return MovimientoInventario.objects.create(
        insumo=insumo, tipo="entrega", cantidad=cantidad_base,
        stock_anterior=general_antes, stock_resultante=insumo.stock,
        trabajador=trabajador,
        stock_trabajador_anterior=trabajador_antes, stock_trabajador_resultante=inv.stock,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, cantidad_base),
        usuario=usuario, observacion=observacion or f"Entrega a {trabajador}",
    )


@transaction.atomic
def devolver_de_trabajador(*, insumo, trabajador, cantidad_base, usuario=None, observacion=""):
    insumo = insumo.__class__.objects.select_for_update().get(pk=insumo.pk)
    inv = InventarioTrabajador.objects.select_for_update().get(trabajador=trabajador, insumo=insumo)
    cantidad_base = decimal_positivo(cantidad_base)
    if Decimal(inv.stock) < cantidad_base:
        raise ValueError(f"Stock insuficiente del trabajador. Disponible: {inv.stock} {insumo.unidad_corta}.")

    general_antes = Decimal(insumo.stock)
    trabajador_antes = Decimal(inv.stock)
    insumo.stock = general_antes + cantidad_base
    inv.stock = trabajador_antes - cantidad_base
    insumo.save(update_fields=["stock"])
    inv.save(update_fields=["stock", "actualizado_en"])

    return MovimientoInventario.objects.create(
        insumo=insumo, tipo="devolucion", cantidad=cantidad_base,
        stock_anterior=general_antes, stock_resultante=insumo.stock,
        trabajador=trabajador,
        stock_trabajador_anterior=trabajador_antes, stock_trabajador_resultante=inv.stock,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, cantidad_base),
        usuario=usuario, observacion=observacion or f"Devolución de {trabajador}",
    )


@transaction.atomic
def consumir_trabajador(*, insumo, trabajador, cantidad_base, mantenimiento, usuario=None, observacion=""):
    inv = InventarioTrabajador.objects.select_for_update().get(trabajador=trabajador, insumo=insumo)
    cantidad_base = decimal_positivo(cantidad_base)
    if Decimal(inv.stock) < cantidad_base:
        raise ValueError(f"Stock insuficiente. Disponible: {inv.stock} {insumo.unidad_corta}.")

    antes = Decimal(inv.stock)
    inv.stock = antes - cantidad_base
    inv.save(update_fields=["stock", "actualizado_en"])

    movimiento = MovimientoInventario.objects.create(
        insumo=insumo, tipo="mantenimiento", cantidad=cantidad_base,
        stock_anterior=Decimal(insumo.stock), stock_resultante=Decimal(insumo.stock),
        trabajador=trabajador, stock_trabajador_anterior=antes, stock_trabajador_resultante=inv.stock,
        mantenimiento=mantenimiento,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, cantidad_base),
        usuario=usuario, observacion=observacion or f"Consumo en mantenimiento #{mantenimiento.pk}",
    )
    return movimiento


@transaction.atomic
def revertir_consumo(*, uso, usuario=None):
    origen = getattr(uso, "origen_inventario", "trabajador") or "trabajador"
    cantidad = Decimal(uso.cantidad)

    if origen == "cliente":
        return

    if origen == "contrato":
        contrato = uso.mantenimiento.contrato
        inv, _ = InventarioContrato.objects.select_for_update().get_or_create(contrato=contrato, insumo=uso.insumo)
        _materializar_estimado_contrato(inv)
        antes = Decimal(inv.stock)
        inv.stock = (antes + cantidad).quantize(Q3)
        from django.utils import timezone
        inv.fecha_referencia_estimacion = timezone.localdate()
        inv.save(update_fields=["stock", "fecha_referencia_estimacion", "actualizado_en"] )
        MovimientoInventario.objects.create(
            insumo=uso.insumo, tipo="ajuste_contrato", cantidad=cantidad,
            stock_anterior=Decimal(uso.insumo.stock), stock_resultante=Decimal(uso.insumo.stock),
            contrato=contrato, trabajador=uso.trabajador, mantenimiento=uso.mantenimiento,
            stock_contrato_anterior=antes, stock_contrato_resultante=inv.stock,
            costo_unitario=uso.costo_unitario or uso.insumo.costo or 0,
            total_costo=-(Decimal(uso.costo_total or 0)), usuario=usuario,
            observacion=f"Reverso de consumo del contrato en mantenimiento #{uso.mantenimiento_id}",
        )
        return

    if not uso.trabajador_id:
        return
    inv, _ = InventarioTrabajador.objects.select_for_update().get_or_create(trabajador=uso.trabajador, insumo=uso.insumo)
    antes = Decimal(inv.stock)
    inv.stock = antes + cantidad
    inv.save(update_fields=["stock", "actualizado_en"])
    MovimientoInventario.objects.create(
        insumo=uso.insumo, tipo="ajuste", cantidad=cantidad,
        stock_anterior=Decimal(uso.insumo.stock), stock_resultante=Decimal(uso.insumo.stock),
        trabajador=uso.trabajador, stock_trabajador_anterior=antes, stock_trabajador_resultante=inv.stock,
        mantenimiento=uso.mantenimiento,
        costo_unitario=uso.costo_unitario or uso.insumo.costo or 0,
        total_costo=-(Decimal(uso.costo_total or 0)), usuario=usuario,
        observacion=f"Reverso de consumo eliminado/ajustado en mantenimiento #{uso.mantenimiento_id}",
    )

def _materializar_estimado_contrato(inv, hoy=None):
    from django.utils import timezone
    hoy = hoy or timezone.localdate()
    referencia = inv.fecha_referencia_estimacion or hoy
    dias = max((hoy - referencia).days, 0)
    if dias > 0 and Decimal(inv.consumo_diario_estimado or 0) > 0:
        consumido = Decimal(inv.consumo_diario_estimado or 0) * Decimal(dias)
        inv.stock = max(Decimal(inv.stock or 0) - consumido, Decimal("0.000")).quantize(Q3)
        inv.fecha_referencia_estimacion = hoy
        inv.save(update_fields=["stock", "fecha_referencia_estimacion", "actualizado_en"])
    elif referencia != hoy:
        inv.fecha_referencia_estimacion = hoy
        inv.save(update_fields=["fecha_referencia_estimacion", "actualizado_en"])
    return inv


@transaction.atomic
def reponer_contrato(*, contrato, insumo, cantidad_base, usuario=None, trabajador=None, observacion=""):
    insumo = insumo.__class__.objects.select_for_update().get(pk=insumo.pk)
    cantidad_base = decimal_positivo(cantidad_base)
    if Decimal(insumo.stock) < cantidad_base:
        raise ValueError(f"Stock general insuficiente. Disponible: {insumo.stock} {insumo.unidad_corta}.")

    inv, _ = InventarioContrato.objects.select_for_update().get_or_create(contrato=contrato, insumo=insumo)
    _materializar_estimado_contrato(inv)
    general_antes = Decimal(insumo.stock)
    contrato_antes = Decimal(inv.stock)
    insumo.stock = (general_antes - cantidad_base).quantize(Q3)
    inv.stock = (contrato_antes + cantidad_base).quantize(Q3)
    from django.utils import timezone
    inv.fecha_referencia_estimacion = timezone.localdate()
    insumo.save(update_fields=["stock"] )
    inv.save(update_fields=["stock", "fecha_referencia_estimacion", "actualizado_en"] )

    return MovimientoInventario.objects.create(
        insumo=insumo, tipo="reposicion_contrato", cantidad=cantidad_base,
        stock_anterior=general_antes, stock_resultante=insumo.stock,
        contrato=contrato, trabajador=trabajador,
        stock_contrato_anterior=contrato_antes, stock_contrato_resultante=inv.stock,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, cantidad_base),
        usuario=usuario, observacion=observacion or f"Reposición al contrato #{contrato.pk}",
    )


@transaction.atomic
def consumir_contrato(*, contrato, insumo, cantidad_base, mantenimiento=None, usuario=None, trabajador=None, observacion=""):
    inv = InventarioContrato.objects.select_for_update().get(contrato=contrato, insumo=insumo)
    _materializar_estimado_contrato(inv)
    cantidad_base = decimal_positivo(cantidad_base)
    if Decimal(inv.stock) < cantidad_base:
        raise ValueError(f"Stock del contrato insuficiente. Disponible estimado: {inv.stock} {insumo.unidad_corta}.")
    antes = Decimal(inv.stock)
    inv.stock = (antes - cantidad_base).quantize(Q3)
    from django.utils import timezone
    inv.fecha_referencia_estimacion = timezone.localdate()
    inv.save(update_fields=["stock", "fecha_referencia_estimacion", "actualizado_en"] )
    return MovimientoInventario.objects.create(
        insumo=insumo, tipo="consumo_contrato", cantidad=cantidad_base,
        stock_anterior=Decimal(insumo.stock), stock_resultante=Decimal(insumo.stock),
        contrato=contrato, trabajador=trabajador, mantenimiento=mantenimiento,
        stock_contrato_anterior=antes, stock_contrato_resultante=inv.stock,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, cantidad_base),
        usuario=usuario, observacion=observacion or f"Consumo del inventario del contrato #{contrato.pk}",
    )


@transaction.atomic
def ajustar_inventario_contrato(*, contrato, insumo, nueva_existencia, usuario=None, trabajador=None, observacion=""):
    inv, _ = InventarioContrato.objects.select_for_update().get_or_create(contrato=contrato, insumo=insumo)
    _materializar_estimado_contrato(inv)
    try:
        nueva = Decimal(str(nueva_existencia).replace(",", ".")).quantize(Q3)
    except Exception:
        raise ValueError("La existencia física no es válida.")
    if nueva < 0:
        raise ValueError("La existencia física no puede ser negativa.")
    antes = Decimal(inv.stock)
    inv.stock = nueva
    from django.utils import timezone
    inv.fecha_referencia_estimacion = timezone.localdate()
    inv.save(update_fields=["stock", "fecha_referencia_estimacion", "actualizado_en"] )
    diferencia = nueva - antes
    return MovimientoInventario.objects.create(
        insumo=insumo, tipo="ajuste_contrato", cantidad=abs(diferencia),
        stock_anterior=Decimal(insumo.stock), stock_resultante=Decimal(insumo.stock),
        contrato=contrato, trabajador=trabajador,
        stock_contrato_anterior=antes, stock_contrato_resultante=nueva,
        costo_unitario=insumo.costo or 0, total_costo=_costo_total(insumo, abs(diferencia)),
        usuario=usuario, observacion=observacion or "Verificación física del inventario en sitio",
    )
