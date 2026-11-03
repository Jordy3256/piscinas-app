from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0025_registro_empresarial_detallado")]
    operations = [
        migrations.CreateModel(name="SuscripcionPushDigital", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("endpoint", models.TextField(unique=True)),
            ("p256dh", models.TextField()),
            ("auth", models.TextField()),
            ("creado_en", models.DateTimeField(auto_now_add=True)),
            ("actualizado_en", models.DateTimeField(auto_now=True)),
            ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="suscripciones_push_digitales", to="asistente_tecnico.perfilsuscriptor")),
        ], options={"verbose_name": "Dispositivo push AQUO360", "verbose_name_plural": "Dispositivos push AQUO360"}),
        migrations.CreateModel(name="EntregaPushDigital", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("estado", models.CharField(max_length=12, default="pendiente", choices=[("pendiente", "Pendiente"), ("enviando", "Enviando"), ("enviado", "Enviado"), ("fallido", "Fallido")])),
            ("intentos", models.PositiveSmallIntegerField(default=0)),
            ("ultimo_intento", models.DateTimeField(null=True, blank=True)),
            ("enviado_en", models.DateTimeField(null=True, blank=True)),
            ("notificacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entregas_push", to="asistente_tecnico.notificaciondigital")),
            ("suscripcion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="entregas_push", to="asistente_tecnico.suscripcionpushdigital")),
        ]),
        migrations.AddConstraint(model_name="entregapushdigital", constraint=models.UniqueConstraint(fields=("notificacion", "suscripcion"), name="uq_aquo_push_aviso_dispositivo")),
    ]
