from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def seed_motor(apps, schema_editor):
    Motor = apps.get_model("asistente_tecnico", "MotorRecomendacion")
    Motor.objects.get_or_create(
        version="1.0",
        defaults={
            "nombre": "Motor JVAQUA",
            "descripcion": "Primera versión del motor de recomendaciones basado en protocolos operativos JVAQUA.",
            "activo": True,
            "reglas": {
                "ph_min": 7.2,
                "ph_max": 7.6,
                "ph_objetivo_normal": 7.4,
                "ph_objetivo_pre_floculacion": 7.8,
                "cloro_min": 1.0,
                "cloro_max": 3.0,
                "cloro_objetivo_normal": 1.5,
                "cloro_objetivo_alto_uso": 2.0,
                "cloro_objetivo_turbidez": 3.0,
                "cloro_objetivo_floculacion": 3.5,
                "cloro_granulado_g_por_m3": 7.0,
                "sulfato_kg_por_tramo": 1.0,
                "sulfato_tramo_m3": 25.0,
                "sulfato_tolerancia_m3": 5.0,
                "alguicida_g_por_25m3": 50.0,
                "p24_g_min_por_25m3": 250.0,
                "p24_g_max_por_25m3": 350.0,
                "seguimiento_horas": 24,
            },
        },
    )


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("trabajadores", "0004_pago_fin_periodo_servicio"),
    ]
    operations = [
        migrations.CreateModel(
            name="MotorRecomendacion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.CharField(max_length=20, unique=True)),
                ("nombre", models.CharField(default="Motor JVAQUA", max_length=120)),
                ("descripcion", models.TextField(blank=True, default="")),
                ("reglas", models.JSONField(blank=True, default=dict)),
                ("activo", models.BooleanField(db_index=True, default=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("publicado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="motores_tecnicos_publicados", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-creado_en", "-id"]},
        ),
        migrations.CreateModel(
            name="CasoAsistenteTecnico",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("volumen_m3", models.DecimalField(decimal_places=2, max_digits=9)),
                ("ph_inicial", models.DecimalField(decimal_places=2, max_digits=4)),
                ("cloro_inicial", models.DecimalField(decimal_places=2, max_digits=5)),
                ("estado_agua", models.CharField(choices=[("transparente", "Transparente"), ("ligeramente_turbia", "Ligeramente turbia"), ("muy_turbia", "Muy turbia"), ("verde", "Verde")], max_length=30)),
                ("tipo_piscina", models.CharField(choices=[("residencial", "Residencial"), ("condominio", "Condominio / urbanización"), ("hotel", "Hotel / hostería"), ("publica", "Piscina pública / alto uso")], max_length=30)),
                ("diagnostico", models.CharField(max_length=120)),
                ("tipo_tratamiento", models.CharField(db_index=True, max_length=40)),
                ("prioridad", models.CharField(default="media", max_length=20)),
                ("resumen", models.TextField(blank=True, default="")),
                ("protocolo", models.JSONField(blank=True, default=list)),
                ("productos_sugeridos", models.JSONField(blank=True, default=list)),
                ("explicaciones", models.JSONField(blank=True, default=dict)),
                ("advertencias", models.JSONField(blank=True, default=list)),
                ("foto_inicial", models.ImageField(blank=True, null=True, upload_to="asistente_tecnico/inicial/")),
                ("foto_final", models.ImageField(blank=True, null=True, upload_to="asistente_tecnico/final/")),
                ("resultado", models.CharField(choices=[("pendiente", "Pendiente de seguimiento"), ("exitoso", "Funcionó completamente"), ("parcial", "Funcionó parcialmente"), ("fallido", "No funcionó")], db_index=True, default="pendiente", max_length=20)),
                ("fallas", models.JSONField(blank=True, default=list)),
                ("observaciones_resultado", models.TextField(blank=True, default="")),
                ("accion_final", models.TextField(blank=True, default="")),
                ("ph_final", models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True)),
                ("cloro_final", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("estado_agua_final", models.CharField(blank=True, choices=[("transparente", "Transparente"), ("ligeramente_turbia", "Ligeramente turbia"), ("muy_turbia", "Muy turbia"), ("verde", "Verde")], default="", max_length=30)),
                ("seguimiento_programado_para", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("seguimiento_respondido_en", models.DateTimeField(blank=True, null=True)),
                ("ultimo_recordatorio_en", models.DateTimeField(blank=True, null=True)),
                ("recordatorios_enviados", models.PositiveSmallIntegerField(default=0)),
                ("destacado", models.BooleanField(db_index=True, default=False)),
                ("nota_destacado", models.TextField(blank=True, default="")),
                ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("motor", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="casos", to="asistente_tecnico.motorrecomendacion")),
                ("trabajador", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="casos_asistente_tecnico", to="trabajadores.trabajador")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="casos_asistente_tecnico", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-creado_en", "-id"]},
        ),
        migrations.AddIndex(model_name="casoasistentetecnico", index=models.Index(fields=["user", "creado_en"], name="ati_user_created_idx")),
        migrations.AddIndex(model_name="casoasistentetecnico", index=models.Index(fields=["resultado", "seguimiento_programado_para"], name="ati_result_follow_idx")),
        migrations.AddIndex(model_name="casoasistentetecnico", index=models.Index(fields=["tipo_tratamiento", "resultado"], name="ati_type_result_idx")),
        migrations.RunPython(seed_motor, migrations.RunPython.noop),
    ]
