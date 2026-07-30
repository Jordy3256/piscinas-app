from datetime import date, timedelta

from django.db import migrations, models


def completar_fechas(apps, schema_editor):
    Obligacion = apps.get_model("finanzas", "ObligacionTrabajador")
    Factura = apps.get_model("finanzas", "Factura")

    for obligacion in Obligacion.objects.all().iterator():
        factura = (
            Factura.objects
            .filter(
                contrato_id=obligacion.contrato_id,
                periodo_anio=obligacion.periodo_anio,
                periodo_mes=obligacion.periodo_mes,
            )
            .only("fecha_vencimiento")
            .first()
        )
        fecha_programada = (
            factura.fecha_vencimiento
            if factura and factura.fecha_vencimiento
            else date(obligacion.periodo_anio, obligacion.periodo_mes, 1) + timedelta(days=5)
        )
        obligacion.fecha_pago_programada = fecha_programada
        obligacion.save(update_fields=["fecha_pago_programada"])


class Migration(migrations.Migration):
    dependencies = [
        ("finanzas", "0007_nomina_operativa"),
    ]

    operations = [
        migrations.AddField(
            model_name="obligaciontrabajador",
            name="fecha_pago_programada",
            field=models.DateField(
                blank=True,
                db_index=True,
                null=True,
                help_text="Fecha prevista para pagar al trabajador; coincide con la fecha de cobro del contrato en este periodo.",
            ),
        ),
        migrations.RunPython(completar_fechas, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="obligaciontrabajador",
            name="fecha_pago_programada",
            field=models.DateField(
                db_index=True,
                help_text="Fecha prevista para pagar al trabajador; coincide con la fecha de cobro del contrato en este periodo.",
            ),
        ),
    ]
