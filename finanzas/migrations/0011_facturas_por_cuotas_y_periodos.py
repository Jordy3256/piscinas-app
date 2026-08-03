from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contratos", "0007_motor_comercial_financiero"), ("finanzas", "0010_pago_consolidado_trabajador")]
    operations = [
        migrations.RemoveConstraint(model_name="factura", name="unique_factura_por_contrato_y_periodo"),
        migrations.AddField(model_name="factura", name="periodo_inicio", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="factura", name="periodo_fin", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="factura", name="cuota_numero", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name="factura", name="total_cuotas", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name="factura", name="fecha_cobro_desde", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="factura", name="fecha_facturacion_programada", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="factura", name="requiere_factura", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="factura", name="factura_enviada", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="factura", name="factura_enviada_en", field=models.DateField(blank=True, null=True)),
        migrations.AddConstraint(model_name="factura", constraint=models.UniqueConstraint(fields=("contrato", "periodo_anio", "periodo_mes", "cuota_numero"), name="unique_factura_cuota_por_contrato_periodo")),
    ]
