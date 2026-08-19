from django.db import migrations, models
import django.db.models.deletion


def copiar_ubicacion_cliente(apps, schema_editor):
    Contrato = apps.get_model("contratos", "Contrato")
    for c in Contrato.objects.select_related("cliente").all().iterator():
        cli = c.cliente
        c.ciudad = cli.ciudad or ""
        c.ciudad_ref_id = cli.ciudad_ref_id
        c.sector_urbanizacion = cli.sector_urbanizacion or ""
        c.direccion = cli.direccion or ""
        c.enlace_google_maps = cli.enlace_google_maps or ""
        c.latitud = cli.latitud
        c.longitud = cli.longitud
        c.save(update_fields=["ciudad","ciudad_ref","sector_urbanizacion","direccion","enlace_google_maps","latitud","longitud"])

class Migration(migrations.Migration):
    dependencies=[("contratos","0012_cotizador_inteligente_ficha_tecnica"),("clientes","0003_cliente_coordenadas_gps")]
    operations=[
        migrations.AddField(model_name="contrato",name="ciudad",field=models.CharField(blank=True,default="",max_length=100)),
        migrations.AddField(model_name="contrato",name="ciudad_ref",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="contratos",to="clientes.ciudad")),
        migrations.AddField(model_name="contrato",name="sector_urbanizacion",field=models.CharField(blank=True,default="",max_length=150)),
        migrations.AddField(model_name="contrato",name="direccion",field=models.TextField(blank=True,default="")),
        migrations.AddField(model_name="contrato",name="enlace_google_maps",field=models.URLField(blank=True,default="",max_length=500)),
        migrations.AddField(model_name="contrato",name="latitud",field=models.DecimalField(blank=True,decimal_places=6,max_digits=9,null=True)),
        migrations.AddField(model_name="contrato",name="longitud",field=models.DecimalField(blank=True,decimal_places=6,max_digits=9,null=True)),
        migrations.RunPython(copiar_ubicacion_cliente, migrations.RunPython.noop),
    ]
