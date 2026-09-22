from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("mantenimientos", "0013_usoinsumo_origen_inventario"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mantenimiento",
            name="estado",
            field=models.CharField(choices=[("pendiente", "Pendiente"), ("realizado", "Realizado"), ("cancelado", "Cancelado")], default="pendiente", max_length=20),
        ),
        migrations.AddField(
            model_name="mantenimiento",
            name="motivo_cancelacion",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="mantenimiento",
            name="cancelado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="mantenimiento",
            name="cancelado_por",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="mantenimientos_cancelados", to=settings.AUTH_USER_MODEL),
        ),
    ]
