from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('mantenimientos','0005_fotomantenimiento')]
    operations = [migrations.CreateModel(name='ChecklistMantenimiento', fields=[
        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
        ('aspirado', models.BooleanField(default=False)),('cepillado', models.BooleanField(default=False)),('recoleccion_basura', models.BooleanField(default=False)),('limpieza_filtros', models.BooleanField(default=False)),('retrolavado_arena', models.BooleanField(default=False)),
        ('cloro_granulado', models.BooleanField(default=False)),('tricloro', models.BooleanField(default=False)),('alguicida', models.BooleanField(default=False)),('metasilicato', models.BooleanField(default=False)),('floculante', models.BooleanField(default=False)),
        ('bomba_estado', models.CharField(blank=True, choices=[('correcto','Funciona correctamente'),('novedad','Presenta novedad')], max_length=20)),('bomba_novedad', models.TextField(blank=True)),
        ('filtro_estado', models.CharField(blank=True, choices=[('correcto','Funciona correctamente'),('novedad','Presenta novedad')], max_length=20)),('filtro_novedad', models.TextField(blank=True)),
        ('nivel_agua', models.CharField(blank=True, choices=[('bajo','Bajo'),('alto','Alto'),('normal','Normal')], max_length=20)),('actualizado_en', models.DateTimeField(auto_now=True)),
        ('mantenimiento', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='checklist_v2', to='mantenimientos.mantenimiento')),
    ])]
