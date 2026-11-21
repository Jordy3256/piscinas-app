from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [
        ('portal_clientes', '0001_initial'),
        ('clientes', '0001_initial'),
        ('contratos', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(name='ConversacionSoporte', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('creada_en', models.DateTimeField(auto_now_add=True)),
            ('actualizada_en', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
            ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='conversaciones_soporte', to='clientes.cliente')),
            ('contrato', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='conversaciones_soporte', to='contratos.contrato')),
        ], options={'ordering': ['-actualizada_en', '-pk']}),
        migrations.CreateModel(name='MensajeSoporte', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('es_cliente', models.BooleanField()),
            ('contenido', models.TextField(max_length=2000)),
            ('creado_en', models.DateTimeField(auto_now_add=True)),
            ('leido_en', models.DateTimeField(blank=True, null=True)),
            ('autor', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ('conversacion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='mensajes', to='portal_clientes.conversacionsoporte')),
        ], options={'ordering': ['creado_en', 'pk']}),
    ]
