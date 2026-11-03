from django.db import migrations, models
import asistente_tecnico.private_storage


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0028_aviso_admin_aquo_aislado")]

    operations = [
        migrations.AlterField(
            model_name="solicitudsuscripciondigital",
            name="comprobante",
            field=models.FileField(
                storage=asistente_tecnico.private_storage.private_aquo_storage,
                upload_to="comprobantes/%Y/%m/",
                null=True,
                blank=True,
            ),
        ),
    ]
