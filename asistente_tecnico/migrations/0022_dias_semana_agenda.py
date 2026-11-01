from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0021_ficha_profesional_digital')]
    operations = [migrations.AddField(model_name='planmantenimientopiscina', name='dias_semana', field=models.JSONField(blank=True, default=list))]
