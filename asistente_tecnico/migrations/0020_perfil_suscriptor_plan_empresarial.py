from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0019_soporte_digital_chat")]

    operations = [
        migrations.AlterField(
            model_name="perfilsuscriptor",
            name="plan",
            field=models.CharField(
                max_length=30, default="individual",
                choices=[
                    ("individual", "Plan Individual"),
                    ("esencial", "Plan Esencial"),
                    ("profesional", "Plan Profesional"),
                    ("empresarial", "Plan Empresarial"),
                ],
            ),
        ),
    ]
