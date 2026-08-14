from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("mantenimientos", "0007_mantenimiento_automatico")]
    operations = [
        migrations.AddField(model_name="mantenimiento", name="estado_agua_rapido", field=models.CharField(blank=True, choices=[("", "Sin seleccionar"), ("cristalina", "Agua cristalina"), ("turbidez", "Ligera turbidez"), ("verde", "Agua verde")], default="", max_length=20)),
        migrations.AddField(model_name="mantenimiento", name="equipo_rapido", field=models.CharField(blank=True, choices=[("", "Sin seleccionar"), ("correcto", "Todo funcionando correctamente"), ("bomba_ruido", "Bomba con ruido"), ("filtro_revision", "Filtro requiere revisión")], default="", max_length=30)),
        migrations.AddField(model_name="mantenimiento", name="recomendaciones_rapidas", field=models.JSONField(blank=True, default=list)),
        migrations.AddField(model_name="mantenimiento", name="borrador_guardado", field=models.BooleanField(default=False)),
    ]
