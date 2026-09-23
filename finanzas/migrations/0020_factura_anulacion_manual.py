from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finanzas", "0019_avisofacturacion_por_visita"),
    ]

    operations = [
        migrations.AddField(
            model_name="factura",
            name="anulada_manual",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="factura",
            name="anulada_manual_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="factura",
            name="anulada_manual_por",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="facturas_anuladas_manualmente",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
