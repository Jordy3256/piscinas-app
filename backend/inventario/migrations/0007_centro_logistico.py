from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


def asignar_codigos(apps, schema_editor):
    Insumo = apps.get_model('inventario', 'Insumo')
    prefijos = {
        'quimicos': 'QUI', 'repuestos': 'REP', 'herramientas': 'HER',
        'equipos': 'EQU', 'construccion': 'MAT', 'otros': 'OTR',
    }
    contadores = {}
    for item in Insumo.objects.order_by('id'):
        if item.codigo:
            continue
        prefijo = prefijos.get(item.categoria, 'PRO')
        contadores[prefijo] = contadores.get(prefijo, 0) + 1
        codigo = f'JVQ-{prefijo}-{contadores[prefijo]:04d}'
        while Insumo.objects.filter(codigo=codigo).exclude(pk=item.pk).exists():
            contadores[prefijo] += 1
            codigo = f'JVQ-{prefijo}-{contadores[prefijo]:04d}'
        item.codigo = codigo
        item.save(update_fields=['codigo'])


class Migration(migrations.Migration):
    dependencies = [
        ('inventario', '0006_inventario_inteligente'),
        ('trabajadores', '0004_pago_fin_periodo_servicio'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name='insumo', name='marca', field=models.CharField(blank=True, default='', max_length=80)),
        migrations.AddField(model_name='insumo', name='modelo', field=models.CharField(blank=True, default='', max_length=80)),
        migrations.AddField(model_name='insumo', name='descripcion', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='insumo', name='controla_inventario', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='comprainsumo', name='lote', field=models.CharField(blank=True, db_index=True, default='', max_length=80)),
        migrations.AddField(model_name='comprainsumo', name='fecha_fabricacion', field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name='comprainsumo', name='fecha_vencimiento', field=models.DateField(blank=True, db_index=True, null=True)),
        migrations.CreateModel(
            name='SolicitudReposicion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stock_al_solicitar', models.DecimalField(decimal_places=3, default=Decimal('0.000'), max_digits=12)),
                ('cantidad_sugerida', models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
                ('observacion', models.CharField(blank=True, default='', max_length=255)),
                ('estado', models.CharField(choices=[('pendiente','Pendiente'),('atendida','Atendida'),('cancelada','Cancelada')], db_index=True, default='pendiente', max_length=15)),
                ('creada_en', models.DateTimeField(auto_now_add=True)),
                ('atendida_en', models.DateTimeField(blank=True, null=True)),
                ('atendida_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes_reposicion_atendidas', to=settings.AUTH_USER_MODEL)),
                ('insumo', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='solicitudes_reposicion', to='inventario.insumo')),
                ('trabajador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitudes_reposicion', to='trabajadores.trabajador')),
            ],
            options={'verbose_name':'Solicitud de reposición','verbose_name_plural':'Solicitudes de reposición','ordering':['-creada_en','-id']},
        ),
        migrations.RunPython(asignar_codigos, migrations.RunPython.noop),
    ]
