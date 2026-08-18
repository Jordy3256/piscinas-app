from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0002_cliente_datos_app"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="latitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name="cliente",
            name="longitud",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
    ]
