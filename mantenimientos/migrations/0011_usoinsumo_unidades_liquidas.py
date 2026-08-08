from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0008_unidades_kg_litros"),
        ("mantenimientos", "0010_checklist_limpieza_filos"),
    ]

    operations = [
        migrations.AlterField(
            model_name="usoinsumo",
            name="unidad_registro",
            field=models.CharField(
                choices=[
                    ("g", "Gramos"),
                    ("kg", "Kilogramos"),
                    ("ml", "Mililitros"),
                    ("l", "Litros"),
                ],
                default="kg",
                max_length=10,
            ),
        ),
    ]
