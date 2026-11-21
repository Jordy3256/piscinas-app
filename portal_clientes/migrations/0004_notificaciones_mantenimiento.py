from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [('portal_clientes', '0003_soporte_multimedia'), ('clientes', '0001_initial'), ('mantenimientos', '0001_initial')]
    operations = [
        migrations.CreateModel(name='NotificacionMantenimientoCliente', fields=[
            ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
            ('tipo', models.CharField(max_length=12)),
            ('creada_en', models.DateTimeField(default=django.utils.timezone.now)),
            ('leida_en', models.DateTimeField(blank=True, null=True)),
            ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avisos_portal', to='clientes.cliente')),
            ('mantenimiento', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avisos_portal', to='mantenimientos.mantenimiento')),
        ], options={'ordering':['-creada_en','-pk']}),
        migrations.AddConstraint(model_name='notificacionmantenimientocliente', constraint=models.UniqueConstraint(fields=('cliente','mantenimiento','tipo'), name='portal_aviso_mantenimiento_unico')),
    ]
