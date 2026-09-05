from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrar_planes(apps, schema_editor):
    Perfil = apps.get_model("asistente_tecnico", "PerfilSuscriptor")
    Perfil.objects.filter(plan="basico").update(plan="esencial")
    Perfil.objects.filter(plan="plus").update(plan="profesional")
    Perfil.objects.filter(estado="prueba").update(estado="pendiente")


class Migration(migrations.Migration):
    dependencies = [
        ("asistente_tecnico", "0017_material_audiovisual_academia"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="perfilsuscriptor",
            name="telefono",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
        migrations.AlterField(
            model_name="perfilsuscriptor",
            name="estado",
            field=models.CharField(choices=[("pendiente", "Pendiente de activación"), ("activo", "Activo"), ("pausado", "Pausado"), ("vencido", "Vencido")], db_index=True, default="pendiente", max_length=20),
        ),
        migrations.AlterField(
            model_name="perfilsuscriptor",
            name="plan",
            field=models.CharField(choices=[("individual", "Plan Individual"), ("esencial", "Plan Esencial"), ("profesional", "Plan Profesional")], default="individual", max_length=30),
        ),
        migrations.RunPython(migrar_planes, migrations.RunPython.noop),
        migrations.CreateModel(
            name="SolicitudSuscripcionDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(choices=[("alta", "Nueva suscripción"), ("renovacion", "Renovación")], db_index=True, default="alta", max_length=16)),
                ("plan", models.CharField(choices=[("individual", "Plan Individual"), ("esencial", "Plan Esencial"), ("profesional", "Plan Profesional")], max_length=30)),
                ("valor", models.DecimalField(decimal_places=2, max_digits=8)),
                ("comprobante", models.FileField(blank=True, null=True, upload_to="jvaqua_digital/comprobantes/%Y/%m/")),
                ("metodo_envio", models.CharField(choices=[("plataforma", "Comprobante subido en JVAQUA Digital"), ("whatsapp", "Comprobante enviado por WhatsApp"), ("ambos", "Plataforma y WhatsApp")], default="plataforma", max_length=16)),
                ("observacion_cliente", models.CharField(blank=True, default="", max_length=300)),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente de verificación"), ("aprobada", "Aprobada"), ("rechazada", "Rechazada")], db_index=True, default="pendiente", max_length=16)),
                ("observacion_admin", models.CharField(blank=True, default="", max_length=300)),
                ("creada_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("revisada_en", models.DateTimeField(blank=True, null=True)),
                ("revisada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="suscripciones_digitales_revisadas", to=settings.AUTH_USER_MODEL)),
                ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="solicitudes_suscripcion", to="asistente_tecnico.perfilsuscriptor")),
            ],
            options={"verbose_name": "Solicitud de suscripción JVAQUA Digital", "verbose_name_plural": "Solicitudes de suscripción JVAQUA Digital", "ordering": ["-creada_en", "-id"]},
        ),
    ]
