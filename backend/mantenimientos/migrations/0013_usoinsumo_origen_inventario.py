from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mantenimientos", "0012_alter_mantenimiento_automatico"),
        ("inventario", "0010_inventario_por_contrato"),
    ]

    operations = [
        migrations.AddField(
            model_name="usoinsumo",
            name="origen_inventario",
            field=models.CharField(
                choices=[
                    ("trabajador", "Inventario del trabajador"),
                    ("contrato", "Inventario del contrato"),
                    ("cliente", "Producto proporcionado por el cliente"),
                ],
                db_index=True,
                default="trabajador",
                max_length=20,
            ),
        ),
    ]
