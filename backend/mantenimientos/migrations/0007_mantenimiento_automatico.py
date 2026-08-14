from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("mantenimientos", "0006_checklistmantenimiento"),
    ]

    operations = [
        migrations.AddField(
            model_name="mantenimiento",
            name="automatico",
            field=models.BooleanField(default=False),
        ),
    ]
