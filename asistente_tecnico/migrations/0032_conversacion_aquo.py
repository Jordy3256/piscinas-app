from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0031_consumo_imagen_aquo"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="ConversacionAquo", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("titulo", models.CharField(default="Nueva conversación", max_length=100)),
        ("mensajes", models.JSONField(default=list, blank=True)),
        ("creado_en", models.DateTimeField(auto_now_add=True)),
        ("actualizado_en", models.DateTimeField(auto_now=True, db_index=True)),
        ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="conversaciones_aquo", to=settings.AUTH_USER_MODEL)),
        ("piscina", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="asistente_tecnico.piscinasuscriptor")),
    ], options={"ordering": ["-actualizado_en"]})]
