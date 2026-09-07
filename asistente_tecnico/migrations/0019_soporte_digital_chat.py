from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import asistente_tecnico.models


class Migration(migrations.Migration):
    dependencies = [
        ("asistente_tecnico", "0018_suscripciones_comerciales_digital"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ConversacionSoporteDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("categoria", models.CharField(choices=[("soporte_tecnico","Soporte técnico de piscina"),("aquo","AQUO / recomendaciones"),("plataforma","Ayuda con JVAQUA Digital"),("suscripcion","Suscripción / pago"),("sugerencia","Sugerencia"),("otro","Otro")], db_index=True, default="soporte_tecnico", max_length=24)),
                ("asunto", models.CharField(blank=True, default="", max_length=160)),
                ("estado", models.CharField(choices=[("abierta","Abierta"),("espera_admin","Esperando respuesta de JVAQUA"),("espera_cliente","Esperando respuesta del cliente"),("cerrada","Cerrada")], db_index=True, default="espera_admin", max_length=20)),
                ("ultimo_mensaje_en", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
                ("piscina", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="conversaciones_soporte", to="asistente_tecnico.piscinasuscriptor")),
                ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversaciones_soporte", to="asistente_tecnico.perfilsuscriptor")),
            ],
            options={"ordering":["-ultimo_mensaje_en","-id"],"verbose_name":"Conversación de soporte JVAQUA Digital","verbose_name_plural":"Conversaciones de soporte JVAQUA Digital"},
        ),
        migrations.CreateModel(
            name="MensajeSoporteDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("remitente", models.CharField(choices=[("cliente","Cliente"),("admin","JVAQUA")], db_index=True, max_length=10)),
                ("texto", models.TextField(blank=True, default="")),
                ("leido_cliente", models.BooleanField(db_index=True, default=False)),
                ("leido_admin", models.BooleanField(db_index=True, default=False)),
                ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("autor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mensajes_soporte_digital", to=settings.AUTH_USER_MODEL)),
                ("conversacion", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="mensajes", to="asistente_tecnico.conversacionsoportedigital")),
            ],
            options={"ordering":["creado_en","id"],"verbose_name":"Mensaje de soporte JVAQUA Digital","verbose_name_plural":"Mensajes de soporte JVAQUA Digital"},
        ),
        migrations.CreateModel(
            name="AdjuntoSoporteDigital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("archivo", models.FileField(upload_to=asistente_tecnico.models.soporte_adjunto_upload_to)),
                ("tipo", models.CharField(choices=[("imagen","Imagen"),("video","Video"),("archivo","Archivo")], default="archivo", max_length=12)),
                ("nombre_original", models.CharField(blank=True, default="", max_length=255)),
                ("tamano", models.PositiveBigIntegerField(default=0)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("mensaje", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="adjuntos", to="asistente_tecnico.mensajesoportedigital")),
            ],
            options={"ordering":["id"],"verbose_name":"Adjunto de soporte JVAQUA Digital","verbose_name_plural":"Adjuntos de soporte JVAQUA Digital"},
        ),
    ]
