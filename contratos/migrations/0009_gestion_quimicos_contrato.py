from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("trabajadores", "0001_initial"),
        ("contratos", "0008_alter_contrato_cobro_mes_desfase_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="quimicos_proveedor",
            field=models.CharField(
                choices=[("jvaqua", "JVAQUA"), ("cliente", "Cliente")],
                default="jvaqua",
                help_text="Indica si los químicos son proporcionados por JVAQUA o por el cliente.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="quimicos_almacenamiento",
            field=models.CharField(
                blank=True,
                choices=[("trabajador", "Inventario del trabajador"), ("contrato", "Inventario del contrato (en sitio)")],
                default="trabajador",
                help_text="Cuando JVAQUA proporciona químicos, indica dónde se almacenan.",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="responsable_reposicion",
            field=models.ForeignKey(
                blank=True,
                help_text="Responsable principal de reponer el inventario en sitio. Si se deja vacío, se usa el técnico designado.",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="contratos_reposicion",
                to="trabajadores.trabajador",
            ),
        ),
    ]
