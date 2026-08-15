from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

def convertir_planes(apps, schema_editor):
    Perfil=apps.get_model('asistente_tecnico','PerfilSuscriptor')
    Perfil.objects.filter(plan='digital').update(plan='basico')

class Migration(migrations.Migration):
    dependencies=[('asistente_tecnico','0012_jvaqua_digital_suscriptores')]
    operations=[
        migrations.RunPython(convertir_planes, migrations.RunPython.noop),
        migrations.AlterField(model_name='perfilsuscriptor',name='plan',field=models.CharField(choices=[('basico','JVAQUA Digital Básico'),('plus','JVAQUA Digital Plus')],default='basico',max_length=30)),
        migrations.CreateModel(name='PlanMantenimientoPiscina',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('frecuencia_semanal',models.PositiveSmallIntegerField(choices=[(1,'1 vez por semana'),(2,'2 veces por semana')],default=1)),('retrolavado_dias',models.PositiveSmallIntegerField(default=15)),('arena_deteriorada',models.BooleanField(default=False)),('activo',models.BooleanField(default=True)),('creado_en',models.DateTimeField(auto_now_add=True)),('actualizado_en',models.DateTimeField(auto_now=True)),('piscina',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='plan_mantenimiento',to='asistente_tecnico.piscinasuscriptor'))],options={'verbose_name':'Plan de mantenimiento de piscina','verbose_name_plural':'Planes de mantenimiento de piscinas'}),
        migrations.CreateModel(name='RegistroMantenimientoPiscina',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('fecha',models.DateField(db_index=True,default=django.utils.timezone.localdate)),('visita_numero',models.PositiveSmallIntegerField(default=1)),('ph',models.DecimalField(blank=True,decimal_places=2,max_digits=4,null=True)),('cloro',models.DecimalField(blank=True,decimal_places=2,max_digits=5,null=True)),('tareas',models.JSONField(blank=True,default=list)),('observaciones',models.TextField(blank=True,default='')),('completado',models.BooleanField(default=True)),('creado_en',models.DateTimeField(auto_now_add=True)),('piscina',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='mantenimientos_digitales',to='asistente_tecnico.piscinasuscriptor'))],options={'verbose_name':'Mantenimiento JVAQUA Digital','verbose_name_plural':'Mantenimientos JVAQUA Digital','ordering':['-fecha','-creado_en']})
    ]
