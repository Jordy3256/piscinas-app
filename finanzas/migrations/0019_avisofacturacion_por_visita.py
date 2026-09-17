from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0018_pago_por_visita_sincronizado"),
        ("finanzas", "0018_nomina_fija_trabajador"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="avisofacturacion",
            name="unique_aviso_facturacion_contrato_periodo",
        ),
        migrations.AddField(
            model_name="avisofacturacion",
            name="cuota_numero",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Número de cuota/visita dentro del período. En pago por visita permite varios avisos mensuales.",
            ),
        ),
        migrations.AddConstraint(
            model_name="avisofacturacion",
            constraint=models.UniqueConstraint(
                fields=("contrato", "periodo_anio", "periodo_mes", "cuota_numero"),
                name="unique_aviso_facturacion_cuota_periodo",
            ),
        ),
    ]
