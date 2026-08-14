from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mantenimientos", "0009_usoinsumo_inventario_trabajador"),
    ]

    operations = [
        migrations.AddField(
            model_name="checklistmantenimiento",
            name="limpieza_filos",
            field=models.BooleanField(default=False),
        ),
    ]
