from django.db import migrations, models


def desactivar_ingresos_recurrentes(apps, schema_editor):
    MovimientoRecurrente = apps.get_model("finanzas", "MovimientoRecurrente")
    MovimientoRecurrente.objects.filter(tipo="ingreso", activo=True).update(activo=False)


class Migration(migrations.Migration):
    dependencies = [
        ("finanzas", "0021_egreso_recurrente_trazabilidad"),
    ]

    operations = [
        migrations.RunPython(desactivar_ingresos_recurrentes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="movimientorecurrente",
            name="tipo",
            field=models.CharField(
                choices=[("egreso", "Egreso manual recurrente")],
                max_length=10,
            ),
        ),
    ]
