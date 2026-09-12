from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("trabajadores", "0007_modalidad_remuneracion_fija"),
        ("finanzas", "0017_avisofacturacion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="obligaciontrabajador",
            name="contrato",
            field=models.ForeignKey(
                blank=True,
                help_text="Vacío cuando la obligación corresponde a una mensualidad fija del trabajador.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="obligaciones_trabajador",
                to="contratos.contrato",
            ),
        ),
        migrations.AddConstraint(
            model_name="obligaciontrabajador",
            constraint=models.UniqueConstraint(
                condition=models.Q(("contrato__isnull", True)),
                fields=("trabajador", "periodo_anio", "periodo_mes"),
                name="unique_nomina_fija_trabajador_periodo",
            ),
        ),
    ]
