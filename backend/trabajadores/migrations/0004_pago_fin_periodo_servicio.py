from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("trabajadores", "0003_configuracion_pago_trabajador"),
    ]

    operations = [
        migrations.AddField(
            model_name="trabajador",
            name="dias_despues_fin_periodo",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Días adicionales después del cierre del período de servicio para programar el pago.",
            ),
        ),
        migrations.AlterField(
            model_name="trabajador",
            name="programacion_pago_nomina",
            field=models.CharField(
                choices=[
                    ("fin_periodo", "Al finalizar el período de servicio"),
                    ("fecha_contratos", "Mismas fechas de cobro de los contratos"),
                    ("dia_fijo", "Día fijo mensual"),
                    ("rango", "Rango de días"),
                    ("personalizado", "Personalizado"),
                ],
                default="fecha_contratos",
                max_length=25,
            ),
        ),
    ]
