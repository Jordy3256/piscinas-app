from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("asistente_tecnico", "0027_aviso_renovacion_aquo"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AvisoAdministrativoAquo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("tipo", models.CharField(max_length=15, default="evento", db_index=True, choices=[("evento", "Evento"), ("soporte", "Soporte")])),
                ("titulo", models.CharField(max_length=150)),
                ("mensaje", models.TextField(blank=True)),
                ("url", models.CharField(max_length=250, blank=True)),
                ("leida", models.BooleanField(default=False, db_index=True)),
                ("creada_en", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("usuario", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="avisos_admin_aquo", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-creada_en", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="avisoadministrativoaquo",
            constraint=models.UniqueConstraint(fields=["usuario", "tipo"], condition=models.Q(tipo="soporte"), name="aquo_admin_un_aviso_soporte"),
        ),
    ]
