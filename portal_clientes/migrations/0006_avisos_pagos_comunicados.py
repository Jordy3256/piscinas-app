from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [('portal_clientes','0005_eliminar_avisos_reporte'),('clientes','0005_facturacion_centralizada')]
    operations = [
        migrations.CreateModel(name='AvisoPortal',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('clave',models.CharField(max_length=110)),('tipo',models.CharField(max_length=20)),('titulo',models.CharField(max_length=160)),('detalle',models.TextField(max_length=1500)),('creada_en',models.DateTimeField(default=django.utils.timezone.now)),('leida_en',models.DateTimeField(blank=True,null=True)),('cliente',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='avisos_generales_portal',to='clientes.cliente'))],options={'ordering':['-creada_en','-pk']}),
        migrations.CreateModel(name='ComunicadoPortal',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('titulo',models.CharField(max_length=160)),('contenido',models.TextField(max_length=1500)),('destino',models.CharField(choices=[('todos','Todos los clientes'),('ciudad','Clientes de una ciudad'),('cliente','Cliente individual')],default='todos',max_length=12)),('publicado_en',models.DateTimeField(blank=True,editable=False,null=True)),('creado_en',models.DateTimeField(auto_now_add=True)),('ciudad',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='clientes.ciudad')),('cliente',models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,to='clientes.cliente'))]),
        migrations.AddConstraint(model_name='avisoportal',constraint=models.UniqueConstraint(fields=('cliente','clave'),name='portal_aviso_general_unico')),
    ]
