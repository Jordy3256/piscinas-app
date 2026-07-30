from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("trabajadores", "0002_alter_trabajador_options"),
        ("contratos", "0003_alter_contrato_options_alter_contrato_forma_pago_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="dias_visita",
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AddField(
            model_name="contrato",
            name="generacion_automatica",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="generacion_automatica",
            field=models.BooleanField(
                default=True,
                help_text="Genera automáticamente un mes de mantenimientos futuros.",
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="programado_hasta",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="contrato",
            name="tecnico_designado",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contratos_designados",
                to="trabajadores.trabajador",
            ),
        ),
    ]
