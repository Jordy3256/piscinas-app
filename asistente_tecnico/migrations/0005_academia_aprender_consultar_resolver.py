from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico','0004_biblioteca_quimica_borradores_v1'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name='contenidoacademia',name='acceso',field=models.CharField(choices=[('compartido','Trabajadores y suscriptores'),('interno','Solo JVAQUA'),('suscriptor','Solo suscriptores')],db_index=True,default='compartido',max_length=20)),
        migrations.AddField(model_name='contenidoacademia',name='modulo_curso',field=models.CharField(blank=True,choices=[('fundamentos','1. Fundamentos'),('quimica','2. Química del agua'),('productos','3. Productos químicos'),('mantenimiento','4. Mantenimiento'),('problemas','5. Problemas del agua'),('equipos','6. Equipos'),('preventivo','7. Mantenimiento preventivo'),('avanzado','8. Conocimiento avanzado')],db_index=True,default='',max_length=30)),
        migrations.AddField(model_name='contenidoacademia',name='orden_curso',field=models.PositiveSmallIntegerField(default=0)),
        migrations.CreateModel(name='ProgresoContenidoAcademia',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('completado',models.BooleanField(default=True)),('completado_en',models.DateTimeField(default=django.utils.timezone.now)),('contenido',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='progresos_curso',to='asistente_tecnico.contenidoacademia')),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='progreso_contenido_academia',to=settings.AUTH_USER_MODEL))],options={'ordering':['-completado_en']}),
        migrations.CreateModel(name='FavoritoContenidoAcademia',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('creado_en',models.DateTimeField(auto_now_add=True)),('contenido',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='favoritos',to='asistente_tecnico.contenidoacademia')),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='favoritos_academia',to=settings.AUTH_USER_MODEL))],options={'ordering':['-creado_en']}),
        migrations.CreateModel(name='ConsultaContenidoAcademia',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('consultado_en',models.DateTimeField(db_index=True,default=django.utils.timezone.now)),('contenido',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='consultas',to='asistente_tecnico.contenidoacademia')),('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='consultas_academia',to=settings.AUTH_USER_MODEL))],options={'ordering':['-consultado_en']}),
        migrations.AddConstraint(model_name='progresocontenidoacademia',constraint=models.UniqueConstraint(fields=('user','contenido'),name='ati_unique_user_content_progress')),
        migrations.AddConstraint(model_name='favoritocontenidoacademia',constraint=models.UniqueConstraint(fields=('user','contenido'),name='ati_unique_user_content_favorite')),
        migrations.AddConstraint(model_name='consultacontenidoacademia',constraint=models.UniqueConstraint(fields=('user','contenido'),name='ati_unique_user_content_recent')),
    ]
