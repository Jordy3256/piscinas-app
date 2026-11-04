from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0029_comprobantes_privados"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [migrations.CreateModel(name="ExperienciaAquo", fields=[
        ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("problema", models.TextField(max_length=2000)),
        ("orientacion", models.TextField(max_length=4000)),
        ("tratamiento_aplicado", models.TextField(blank=True, max_length=2000)),
        ("resultado_reportado", models.CharField(choices=[("pendiente", "Pendiente"), ("favorable", "Favorable"), ("parcial", "Parcial"), ("fallido", "Fallido")], db_index=True, default="pendiente", max_length=15)),
        ("observaciones", models.TextField(blank=True, max_length=2000)),
        ("validado_tecnicamente", models.BooleanField(db_index=True, default=False)),
        ("publicado_como_conocimiento", models.BooleanField(db_index=True, default=False)),
        ("creado_en", models.DateTimeField(auto_now_add=True)),
        ("actualizado_en", models.DateTimeField(auto_now=True)),
        ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="experiencias_aquo", to=settings.AUTH_USER_MODEL)),
        ("piscina", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="experiencias_aquo", to="asistente_tecnico.piscinasuscriptor")),
    ], options={"ordering": ["-creado_en"]})]
