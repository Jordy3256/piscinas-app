from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trabajadores", "0006_trabajador_foto_perfil"),
    ]

    operations = [
        migrations.AddField(
            model_name="trabajador",
            name="tipo_remuneracion",
            field=models.CharField(
                choices=[
                    ("por_contrato", "Por contratos"),
                    ("mensual_fija", "Mensualidad fija"),
                ],
                db_index=True,
                default="por_contrato",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="trabajador",
            name="sueldo_mensual_fijo",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Valor mensual fijo. Solo se usa cuando la remuneración es mensual fija.",
                max_digits=12,
            ),
        ),
    ]
