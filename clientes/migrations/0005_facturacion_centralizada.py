from django.db import migrations, models

CAMPOS = ("facturacion_tipo_identificacion", "facturacion_identificacion", "facturacion_razon_social", "facturacion_direccion", "facturacion_telefono", "facturacion_correo")

def copiar_datos_fiscales(apps, schema_editor):
    Cliente = apps.get_model("clientes", "Cliente")
    Contrato = apps.get_model("contratos", "Contrato")
    db = schema_editor.connection.alias
    for cliente in Cliente.objects.using(db).all().iterator():
        contratos = Contrato.objects.using(db).filter(cliente_id=cliente.pk).order_by("pk")
        valores = {}
        conflicto = False
        for campo in CAMPOS:
            distintos = {str(v).strip() for v in contratos.values_list(campo, flat=True) if v and str(v).strip()}
            if len(distintos) > 1:
                conflicto = True
            elif len(distintos) == 1:
                valores[campo] = next(iter(distintos))
        # No elegir datos de un contrato al azar si existe alguna discrepancia.
        if conflicto:
            cliente.facturacion_revision_pendiente = True
            cliente.save(using=db, update_fields=["facturacion_revision_pendiente"])
        else:
            for campo, valor in valores.items():
                setattr(cliente, campo, valor)
            if valores:
                cliente.save(using=db, update_fields=list(valores))

class Migration(migrations.Migration):
    dependencies = [("clientes", "0004_ciudad_estructurada"), ("contratos", "0022_cotizacion_tipo_piscina")]
    operations = [
        migrations.AddField("cliente", "facturacion_tipo_identificacion", models.CharField(max_length=12, blank=True, default="", choices=[("ruc", "RUC"), ("cedula", "Cédula"), ("pasaporte", "Pasaporte"), ("otro", "Otro")])),
        migrations.AddField("cliente", "facturacion_identificacion", models.CharField(max_length=20, blank=True, default="")),
        migrations.AddField("cliente", "facturacion_razon_social", models.CharField(max_length=200, blank=True, default="")),
        migrations.AddField("cliente", "facturacion_direccion", models.CharField(max_length=300, blank=True, default="")),
        migrations.AddField("cliente", "facturacion_telefono", models.CharField(max_length=30, blank=True, default="")),
        migrations.AddField("cliente", "facturacion_correo", models.EmailField(blank=True, default="")),
        migrations.AddField("cliente", "facturacion_revision_pendiente", models.BooleanField(default=False)),
        migrations.RunPython(copiar_datos_fiscales, migrations.RunPython.noop),
    ]
