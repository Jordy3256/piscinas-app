from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("asistente_tecnico", "0014_piscina_origen_agua_hierro"),
    ]

    operations = [
        migrations.AlterField(
            model_name="planmantenimientopiscina",
            name="frecuencia_semanal",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, "1 vez por semana"),
                    (2, "2 veces por semana"),
                    (3, "3 veces por semana"),
                    (4, "4 veces por semana"),
                    (5, "5 veces por semana"),
                    (6, "6 veces por semana"),
                    (7, "7 veces por semana"),
                ],
                default=1,
            ),
        ),
        migrations.CreateModel(
            name="VisitaProgramadaPiscina",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha", models.DateField(db_index=True)),
                ("visita_numero", models.PositiveSmallIntegerField(default=1)),
                ("estado", models.CharField(choices=[("programada", "Programada"), ("completada", "Completada"), ("omitida", "Omitida")], db_index=True, default="programada", max_length=16)),
                ("plan_resultado", models.JSONField(blank=True, default=dict)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("piscina", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visitas_programadas", to="asistente_tecnico.piscinasuscriptor")),
                ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="visitas_programadas", to="asistente_tecnico.planmantenimientopiscina")),
            ],
            options={
                "verbose_name": "Visita programada JVAQUA Digital",
                "verbose_name_plural": "Visitas programadas JVAQUA Digital",
                "ordering": ["fecha", "visita_numero"],
            },
        ),
        migrations.CreateModel(
            name="NotificacionDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("plan_creado", "Plan creado"), ("visita_hoy", "Visita de hoy"), ("recordatorio", "Recordatorio")], db_index=True, default="recordatorio", max_length=20)),
                ("titulo", models.CharField(max_length=150)),
                ("mensaje", models.TextField()),
                ("programada_para", models.DateTimeField(db_index=True)),
                ("leida", models.BooleanField(db_index=True, default=False)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("piscina", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notificaciones_digitales", to="asistente_tecnico.piscinasuscriptor")),
                ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notificaciones_digitales", to="asistente_tecnico.perfilsuscriptor")),
                ("visita", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notificaciones", to="asistente_tecnico.visitaprogramadapiscina")),
            ],
            options={
                "verbose_name": "Notificación JVAQUA Digital",
                "verbose_name_plural": "Notificaciones JVAQUA Digital",
                "ordering": ["-programada_para", "-creada_en"],
            },
        ),
        migrations.AddConstraint(
            model_name="visitaprogramadapiscina",
            constraint=models.UniqueConstraint(fields=("plan", "fecha", "visita_numero"), name="uq_plan_visita_fecha_numero"),
        ),
        migrations.AddConstraint(
            model_name="notificaciondigital",
            constraint=models.UniqueConstraint(fields=("suscriptor", "visita", "tipo"), name="uq_notificacion_digital_visita_tipo"),
        ),
    ]
