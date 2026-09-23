from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("finanzas", "0020_factura_anulacion_manual")]

    operations = [
        migrations.AddField(
            model_name="movimientorecurrente",
            name="dia_mes",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Día original elegido para recurrencias mensuales; conserva, por ejemplo, el día 31 cuando existe.", null=True),
        ),
        migrations.AddField(
            model_name="egreso",
            name="recurrente",
            field=models.ForeignKey(
                blank=True,
                help_text="Gasto recurrente que originó esta obligación, cuando aplica.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="egresos_generados",
                to="finanzas.movimientorecurrente",
            ),
        ),
        migrations.AddField(
            model_name="egreso",
            name="fecha_recurrente",
            field=models.DateField(
                blank=True,
                db_index=True,
                help_text="Fecha programada del gasto recurrente. Evita duplicar una misma obligación.",
                null=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="egreso",
            constraint=models.UniqueConstraint(
                condition=models.Q(("recurrente__isnull", False)),
                fields=("recurrente", "fecha_recurrente"),
                name="uniq_egreso_recurrente_fecha",
            ),
        ),
    ]
