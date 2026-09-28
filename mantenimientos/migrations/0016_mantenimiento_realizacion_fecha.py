from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("mantenimientos", "0015_novedadmantenimiento")]
    operations = [
        migrations.AddField(model_name="mantenimiento", name="realizado_en", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="mantenimiento", name="motivo_fuera_fecha", field=models.CharField(blank=True, choices=[("trabajador", "Responsabilidad del trabajador"), ("cliente", "Solicitud o responsabilidad del cliente"), ("reprogramacion", "Reprogramación autorizada"), ("extraordinario", "Caso extraordinario"), ("otro", "Otro")], default="", max_length=20)),
        migrations.AddField(model_name="mantenimiento", name="nota_fuera_fecha", field=models.TextField(blank=True, default="")),
    ]
