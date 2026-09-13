from django.utils import timezone

from contratos.models import Contrato
from contratos.programacion import mantener_programacion_automatica
from contratos.vencimientos import sincronizar_alertas_vencimiento_contratos
from finanzas.alertas_financieras import generar_alertas_financieras
from finanzas.facturacion_externa import sincronizar_avisos_facturacion
from finanzas.sincronizacion import (
    materializar_nomina_fija_trabajador,
    sincronizar_contrato_activo,
)
from inventario.services import materializar_consumos_contratos
from trabajadores.models import Trabajador


def ejecutar_proceso_diario_jvaqua(*, hoy=None, enviar_push=True, usuario=None):
    """
    Motor diario central del ERP.

    Todas las operaciones son idempotentes: ejecutar el proceso más de una vez
    el mismo día no debe duplicar mantenimientos, Cartera, Nómina ni alertas.
    """
    hoy = hoy or timezone.localdate()
    resultado = {"fecha": hoy.isoformat(), "errores": []}

    # 1. Vigencia contractual y avisos administrativos.
    try:
        resultado["vigencias"] = sincronizar_alertas_vencimiento_contratos(hoy=hoy)
    except Exception as exc:
        resultado["errores"].append({"etapa": "vigencias", "error": str(exc)})

    # 2. Programación operativa.
    try:
        resultado["programacion"] = mantener_programacion_automatica(horizonte_dias=14)
        for item in resultado["programacion"].get("errores", []):
            resultado["errores"].append({"etapa": "programacion", "error": str(item)})
    except Exception as exc:
        resultado["errores"].append({"etapa": "programacion", "error": str(exc)})

    # 3. Cartera + nómina por contrato.
    finanzas = {
        "contratos_procesados": 0,
        "facturas_creadas": 0,
        "facturas_actualizadas": 0,
        "obligaciones_creadas": 0,
        "obligaciones_actualizadas": 0,
    }
    try:
        contratos = (
            Contrato.objects.filter(activo=True)
            .select_related("cliente", "tecnico_designado")
            .order_by("id")
        )
        for contrato in contratos:
            # Los contratos vencidos permanecen visibles/activos para decisión
            # administrativa, pero no generan nuevos ciclos económicos.
            if contrato.fecha_fin_contrato and contrato.fecha_fin_contrato < hoy:
                continue
            try:
                datos = sincronizar_contrato_activo(
                    contrato,
                    desde_fecha=hoy,
                    horizonte_meses=12,
                )
                finanzas["contratos_procesados"] += 1
                for clave in (
                    "facturas_creadas",
                    "facturas_actualizadas",
                    "obligaciones_creadas",
                    "obligaciones_actualizadas",
                ):
                    finanzas[clave] += int(datos.get(clave, 0) or 0)
            except Exception as exc:
                resultado["errores"].append({
                    "etapa": "finanzas_contrato",
                    "contrato_id": contrato.pk,
                    "error": str(exc),
                })
        resultado["finanzas"] = finanzas
    except Exception as exc:
        resultado["errores"].append({"etapa": "finanzas", "error": str(exc)})

    # 4. Mensualidades fijas.
    nomina_fija = {"trabajadores_procesados": 0, "creadas": 0, "actualizadas": 0}
    try:
        trabajadores = Trabajador.objects.filter(
            activo=True,
            tipo_remuneracion="mensual_fija",
            sueldo_mensual_fijo__gt=0,
        )
        for trabajador in trabajadores:
            try:
                datos = materializar_nomina_fija_trabajador(
                    trabajador,
                    desde_fecha=hoy,
                    horizonte_meses=12,
                )
                nomina_fija["trabajadores_procesados"] += 1
                nomina_fija["creadas"] += int(datos.get("creadas", 0) or 0)
                nomina_fija["actualizadas"] += int(datos.get("actualizadas", 0) or 0)
            except Exception as exc:
                resultado["errores"].append({
                    "etapa": "nomina_fija",
                    "trabajador_id": trabajador.pk,
                    "error": str(exc),
                })
        resultado["nomina_fija"] = nomina_fija
    except Exception as exc:
        resultado["errores"].append({"etapa": "nomina_fija", "error": str(exc)})

    # 5. Facturación externa.
    try:
        resultado["facturacion"] = sincronizar_avisos_facturacion(hoy=hoy)
        for item in resultado["facturacion"].get("errores", []):
            resultado["errores"].append({"etapa": "facturacion", "error": str(item)})
    except Exception as exc:
        resultado["errores"].append({"etapa": "facturacion", "error": str(exc)})

    # 6. Inventario automático en sitio.
    try:
        resultado["inventario"] = {
            "registros_procesados": materializar_consumos_contratos(
                hoy=hoy,
                usuario=usuario,
            )
        }
    except Exception as exc:
        resultado["errores"].append({"etapa": "inventario", "error": str(exc)})

    # 7. Alertas financieras, al final para trabajar con información sincronizada.
    try:
        resultado["alertas_financieras"] = {
            "activas": generar_alertas_financieras(enviar_push=enviar_push)
        }
    except Exception as exc:
        resultado["errores"].append({"etapa": "alertas_financieras", "error": str(exc)})

    resultado["ok"] = not resultado["errores"]
    return resultado
