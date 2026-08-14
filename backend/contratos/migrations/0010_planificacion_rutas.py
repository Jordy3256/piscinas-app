from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("contratos", "0009_gestion_quimicos_contrato")]
    operations = [
        migrations.AddField(model_name="contrato", name="tipo_horario_visita", field=models.CharField(choices=[("libre", "Horario libre"), ("fijo", "Hora fija"), ("ventana", "Ventana horaria")], default="libre", help_text="Restricción horaria usada únicamente para sugerir la ruta diaria al técnico.", max_length=20)),
        migrations.AddField(model_name="contrato", name="hora_visita_fija", field=models.TimeField(blank=True, null=True)),
        migrations.AddField(model_name="contrato", name="ventana_visita_desde", field=models.TimeField(blank=True, null=True)),
        migrations.AddField(model_name="contrato", name="ventana_visita_hasta", field=models.TimeField(blank=True, null=True)),
        migrations.AddField(model_name="contrato", name="duracion_estimada_minutos", field=models.PositiveSmallIntegerField(default=30, help_text="Duración orientativa del mantenimiento para planificar la ruta.", validators=[django.core.validators.MinValueValidator(10), django.core.validators.MaxValueValidator(480)])),
        migrations.AddField(model_name="contrato", name="prioridad_visita", field=models.CharField(choices=[("normal", "Normal"), ("alta", "Alta")], default="normal", max_length=10)),
    ]
