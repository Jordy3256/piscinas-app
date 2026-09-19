from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contratos", "0019_cobro_meses_adelantados")]

    operations = [
        migrations.AddField(model_name="contrato", name="facturacion_tipo_identificacion", field=models.CharField(blank=True, choices=[("ruc", "RUC"), ("cedula", "Cédula")], default="", max_length=10)),
        migrations.AddField(model_name="contrato", name="facturacion_identificacion", field=models.CharField(blank=True, default="", max_length=20)),
        migrations.AddField(model_name="contrato", name="facturacion_razon_social", field=models.CharField(blank=True, default="", max_length=200)),
        migrations.AddField(model_name="contrato", name="facturacion_direccion", field=models.CharField(blank=True, default="", max_length=300)),
        migrations.AddField(model_name="contrato", name="facturacion_telefono", field=models.CharField(blank=True, default="", max_length=30)),
        migrations.AddField(model_name="contrato", name="facturacion_correo", field=models.EmailField(blank=True, default="", max_length=254)),
    ]
