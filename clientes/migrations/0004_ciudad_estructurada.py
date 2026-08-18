from django.db import migrations, models
import django.db.models.deletion

def poblar_ciudades(apps, schema_editor):
    Cliente=apps.get_model("clientes","Cliente"); Ciudad=apps.get_model("clientes","Ciudad")
    for c in Cliente.objects.exclude(ciudad="").iterator():
        nombre=(c.ciudad or "").strip().title()
        if not nombre: continue
        obj,_=Ciudad.objects.get_or_create(nombre=nombre)
        c.ciudad_ref_id=obj.id; c.ciudad=nombre; c.save(update_fields=["ciudad_ref","ciudad"])
class Migration(migrations.Migration):
    dependencies=[("clientes","0003_cliente_coordenadas_gps")]
    operations=[
      migrations.CreateModel(name="Ciudad",fields=[("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),("nombre",models.CharField(max_length=100,unique=True)),("activa",models.BooleanField(default=True)),("orden",models.PositiveSmallIntegerField(default=0))],options={"verbose_name":"Ciudad","verbose_name_plural":"Ciudades","ordering":["orden","nombre"]}),
      migrations.AddField(model_name="cliente",name="ciudad_ref",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="clientes",to="clientes.ciudad")),
      migrations.RunPython(poblar_ciudades,migrations.RunPython.noop),
    ]
