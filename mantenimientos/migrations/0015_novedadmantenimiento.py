from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("mantenimientos", "0014_mantenimiento_cancelacion"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NovedadMantenimiento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("detalle", models.TextField()),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("revision", "En revisión"), ("resuelta", "Resuelta")], db_index=True, default="pendiente", max_length=20)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
                ("gestionada_en", models.DateTimeField(blank=True, null=True)),
                ("nota_gestion", models.TextField(blank=True)),
                ("gestionada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="novedades_mantenimiento_gestionadas", to=settings.AUTH_USER_MODEL)),
                ("mantenimiento", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="novedad_administrativa", to="mantenimientos.mantenimiento")),
                ("reportada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="novedades_mantenimiento_reportadas", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Novedad de mantenimiento",
                "verbose_name_plural": "Novedades de mantenimiento",
                "ordering": ["-creada_en"],
            },
        ),
    ]
