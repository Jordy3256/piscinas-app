from django.db import migrations, models


def aislar_recurrentes_existentes(apps, schema_editor):
    MovimientoRecurrente = apps.get_model("finanzas", "MovimientoRecurrente")
    # Todo registro anterior a esta migración pertenece al mecanismo histórico.
    # Se conserva para auditoría, pero queda inactivo y fuera del nuevo módulo.
    MovimientoRecurrente.objects.all().update(
        es_gasto_manual_recurrente=False,
        activo=False,
    )


class Migration(migrations.Migration):
    dependencies = [("finanzas", "0022_recurrentes_solo_egresos_manuales")]

    operations = [
        migrations.AddField(
            model_name="movimientorecurrente",
            name="es_gasto_manual_recurrente",
            field=models.BooleanField(
                default=False,
                db_index=True,
                help_text="Identifica exclusivamente los gastos recurrentes creados manualmente desde la nueva sección de Finanzas.",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(aislar_recurrentes_existentes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="movimientorecurrente",
            name="es_gasto_manual_recurrente",
            field=models.BooleanField(
                default=True,
                db_index=True,
                help_text="Identifica exclusivamente los gastos recurrentes creados manualmente desde la nueva sección de Finanzas.",
            ),
        ),
    ]
