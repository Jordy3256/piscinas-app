from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True
    dependencies = [('clientes','0005_facturacion_centralizada'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name='AccesoCliente', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('codigo_hash', models.CharField(blank=True, max_length=128)),
        ('codigo_expira', models.DateTimeField(blank=True, null=True)),
        ('activado_en', models.DateTimeField(blank=True, null=True)),
        ('habilitado', models.BooleanField(default=True)),
        ('creado_en', models.DateTimeField(auto_now_add=True)),
        ('cliente', models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name='acceso_portal', to='clientes.cliente')),
        ('usuario', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='acceso_cliente_jvaqua', to=settings.AUTH_USER_MODEL)),
    ])]
