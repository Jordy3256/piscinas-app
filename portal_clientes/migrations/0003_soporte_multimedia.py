from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [('portal_clientes', '0002_soporte_chat')]
    operations = [
        migrations.AlterField(model_name='mensajesoporte', name='contenido', field=models.TextField(max_length=2000, blank=True)),
        migrations.AddField(model_name='mensajesoporte', name='archivo', field=models.BinaryField(blank=True, editable=False, null=True)),
        migrations.AddField(model_name='mensajesoporte', name='archivo_tipo', field=models.CharField(blank=True, max_length=80)),
        migrations.AddField(model_name='mensajesoporte', name='archivo_nombre', field=models.CharField(blank=True, max_length=120)),
        migrations.AddField(model_name='mensajesoporte', name='archivo_clase', field=models.CharField(blank=True, max_length=12)),
    ]
