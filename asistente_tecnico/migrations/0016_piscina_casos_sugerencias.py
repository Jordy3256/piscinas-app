from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ("asistente_tecnico", "0015_plan_autonomo_notificaciones"),
    ]

    operations = [
        migrations.AddField(
            model_name="casoasistentetecnico",
            name="piscina",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="casos_asistente",
                to="asistente_tecnico.piscinasuscriptor",
            ),
        ),
        migrations.CreateModel(
            name="SugerenciaDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("categoria", models.CharField(choices=[("general","Aplicación en general"),("aquo","Asistente AQUO"),("plan","Plan semanal"),("curso","Curso"),("biblioteca","Biblioteca"),("piscinas","Mis piscinas"),("otro","Otro")], db_index=True, default="general", max_length=20)),
                ("calificacion", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("mensaje", models.TextField()),
                ("estado", models.CharField(choices=[("nueva","Nueva"),("revision","En revisión"),("considerada","Considerada"),("cerrada","Cerrada")], db_index=True, default="nueva", max_length=20)),
                ("respuesta_interna", models.TextField(blank=True, default="")),
                ("creada_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
                ("piscina", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sugerencias", to="asistente_tecnico.piscinasuscriptor")),
                ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sugerencias_digitales", to="asistente_tecnico.perfilsuscriptor")),
            ],
            options={
                "verbose_name": "Sugerencia JVAQUA Digital",
                "verbose_name_plural": "Sugerencias JVAQUA Digital",
                "ordering": ["-creada_en", "-id"],
            },
        ),
    ]
