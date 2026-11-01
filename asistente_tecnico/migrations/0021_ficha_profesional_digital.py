from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0020_perfil_suscriptor_plan_empresarial")]
    operations = [
        migrations.AddField(model_name="piscinasuscriptor", name="propietario_nombre", field=models.CharField(max_length=150, blank=True, default="")),
        migrations.AddField(model_name="piscinasuscriptor", name="propietario_telefono", field=models.CharField(max_length=35, blank=True, default="")),
        migrations.AddField(model_name="piscinasuscriptor", name="direccion", field=models.CharField(max_length=255, blank=True, default="")),
        migrations.AddField(model_name="piscinasuscriptor", name="ubicacion_referencia", field=models.CharField(max_length=255, blank=True, default="")),
        migrations.AddField(model_name="piscinasuscriptor", name="valor_mensual", field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="piscinasuscriptor", name="dia_cobro", field=models.PositiveSmallIntegerField(null=True, blank=True)),
        migrations.AddField(model_name="piscinasuscriptor", name="recordatorio_cobro_activo", field=models.BooleanField(default=False)),
    ]
