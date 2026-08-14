from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("clientes", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="ciudad",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="cliente",
            name="sector_urbanizacion",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="cliente",
            name="enlace_google_maps",
            field=models.URLField(blank=True, default="", max_length=500),
        ),
        migrations.AlterModelOptions(
            name="cliente",
            options={"ordering": ["nombre", "id"], "verbose_name": "Cliente", "verbose_name_plural": "Clientes"},
        ),
    ]
