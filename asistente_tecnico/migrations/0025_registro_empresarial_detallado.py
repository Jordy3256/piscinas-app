from django.db import migrations, models
import django.db.models.deletion
import asistente_tecnico.private_storage


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0024_cartera_empresarial_digital")]

    operations = [
        migrations.AddField(
            model_name="registromantenimientopiscina", name="visita",
            field=models.OneToOneField(blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="registro_empresarial",
                to="asistente_tecnico.visitaprogramadapiscina"),
        ),
        migrations.AddField(
            model_name="registromantenimientopiscina", name="quimicos",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name="EvidenciaMantenimientoDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imagen", models.ImageField(storage=asistente_tecnico.private_storage.PrivateAquoStorage(), upload_to="mantenimientos/%Y/%m/")),
                ("descripcion", models.CharField(blank=True, default="", max_length=90)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("registro", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                    related_name="evidencias", to="asistente_tecnico.registromantenimientopiscina")),
            ],
            options={"ordering": ["id"], "verbose_name": "Evidencia mantenimiento AQUO360", "verbose_name_plural": "Evidencias mantenimiento AQUO360"},
        ),
    ]
