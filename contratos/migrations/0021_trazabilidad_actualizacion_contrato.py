from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("contratos", "0020_datos_facturacion_contrato"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="ultima_actualizacion",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="contrato",
            name="actualizado_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contratos_actualizados",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
