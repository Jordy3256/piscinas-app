from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("trabajadores", "0005_ciudades_trabajador"),
    ]

    operations = [
        migrations.AddField(
            model_name="trabajador",
            name="foto_perfil",
            field=models.ImageField(blank=True, null=True, upload_to="trabajadores/perfiles/"),
        ),
    ]
