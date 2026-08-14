from django.db import migrations


def sincronizar_inactivos(apps, schema_editor):
    Contrato = apps.get_model("contratos", "Contrato")
    Factura = apps.get_model("finanzas", "Factura")
    Obligacion = apps.get_model("finanzas", "ObligacionTrabajador")

    for contrato in Contrato.objects.filter(activo=False).iterator():
        for factura in Factura.objects.filter(contrato_id=contrato.pk):
            tiene_pagos = factura.pagos.exists() or bool(factura.ingreso_generado_id)
            if tiene_pagos:
                if factura.estado != "anulada":
                    factura.estado = "anulada"
                    factura.save(update_fields=["estado"])
            else:
                factura.delete()

        for obligacion in Obligacion.objects.filter(contrato_id=contrato.pk):
            if obligacion.pagos.exists():
                if obligacion.estado != "anulado":
                    obligacion.estado = "anulado"
                    obligacion.save(update_fields=["estado"])
            else:
                obligacion.delete()


class Migration(migrations.Migration):
    dependencies = [("finanzas", "0008_fecha_pago_programada_nomina")]
    operations = [migrations.RunPython(sincronizar_inactivos, migrations.RunPython.noop)]
