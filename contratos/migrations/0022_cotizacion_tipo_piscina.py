from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contratos", "0021_trazabilidad_actualizacion_contrato")]
    operations = [
        migrations.AddField(
            model_name="cotizacionmantenimiento",
            name="tipo_piscina",
            field=models.CharField(blank=True, default="residencial", max_length=30),
        ),
    ]
