from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("asistente_tecnico", "0016_piscina_casos_sugerencias"),
    ]

    operations = [
        migrations.CreateModel(
            name="MaterialAudiovisualAcademia",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("video", "Video"), ("audio", "Audio")], db_index=True, default="video", max_length=10)),
                ("archivo", models.FileField(upload_to="academia/audiovisual/%Y/%m/")),
                ("titulo", models.CharField(max_length=160)),
                ("descripcion", models.CharField(blank=True, default="", max_length=320)),
                ("duracion_texto", models.CharField(blank=True, default="", help_text="Opcional. Ej.: 45 s, 1:20 min.", max_length=30)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("activo", models.BooleanField(db_index=True, default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("contenido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="materiales_audiovisuales", to="asistente_tecnico.contenidoacademia")),
            ],
            options={
                "verbose_name": "Material audiovisual de Academia",
                "verbose_name_plural": "Material audiovisual de Academia",
                "ordering": ["orden", "id"],
            },
        ),
    ]
