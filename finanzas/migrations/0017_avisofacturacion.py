from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contratos", "0015_contrato_aplica_iva"),
        ("finanzas", "0016_comprobante_servicio"),
    ]

    operations = [
        migrations.CreateModel(
            name="AvisoFacturacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("periodo_anio", models.PositiveIntegerField()),
                ("periodo_mes", models.PositiveSmallIntegerField()),
                ("periodo_inicio", models.DateField()),
                ("periodo_fin", models.DateField()),
                ("fecha_programada", models.DateField(db_index=True)),
                ("estado", models.CharField(
                    choices=[("pendiente", "Pendiente"), ("realizada", "Factura realizada"), ("anulada", "Anulada")],
                    db_index=True,
                    default="pendiente",
                    max_length=12,
                )),
                ("realizada_en", models.DateTimeField(blank=True, null=True)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
                ("contrato", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="avisos_facturacion",
                    to="contratos.contrato",
                )),
                ("realizada_por", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="facturas_externas_realizadas",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "Aviso de facturación",
                "verbose_name_plural": "Avisos de facturación",
                "ordering": ["fecha_programada", "contrato__cliente__nombre", "id"],
            },
        ),
        migrations.AddConstraint(
            model_name="avisofacturacion",
            constraint=models.UniqueConstraint(
                fields=("contrato", "periodo_anio", "periodo_mes"),
                name="unique_aviso_facturacion_contrato_periodo",
            ),
        ),
    ]
