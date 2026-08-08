from django.db import migrations, models


def normalizar_unidades(apps, schema_editor):
    Insumo = apps.get_model("inventario", "Insumo")
    # La versión anterior permitía "unidad". Desde esta versión el inventario
    # operativo de JVAQUA se controla únicamente en kg o L. Los registros
    # antiguos por unidad se conservan como kg para que el valor siga siendo
    # válido y puedan ser corregidos manualmente desde la ficha del producto.
    Insumo.objects.filter(unidad_base="unidad").update(unidad_base="kg")


class Migration(migrations.Migration):
    dependencies = [("inventario", "0007_centro_logistico")]

    operations = [
        migrations.RunPython(normalizar_unidades, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="insumo",
            name="unidad_base",
            field=models.CharField(
                choices=[("kg", "Kilogramos (kg)"), ("l", "Litros (L)")],
                default="kg",
                max_length=10,
            ),
        ),
    ]
