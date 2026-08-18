from django.db import migrations, models
import django.db.models.deletion
class Migration(migrations.Migration):
 dependencies=[("clientes","0004_ciudad_estructurada"),("trabajadores","0004_pago_fin_periodo_servicio")]
 operations=[migrations.AddField(model_name="trabajador",name="ciudad_principal",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="trabajadores_principales",to="clientes.ciudad")),migrations.AddField(model_name="trabajador",name="ciudades_habilitadas",field=models.ManyToManyField(blank=True,related_name="trabajadores_habilitados",to="clientes.ciudad"))]
