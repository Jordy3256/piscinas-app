from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0015_contrato_aplica_iva"),
    ]

    operations = [
        migrations.AlterField(
            model_name="contrato",
            name="forma_pago",
            field=models.CharField(
                blank=True,
                choices=[
                    ("adelantado", "Adelantado"),
                    ("servicio_cumplido", "Servicio cumplido"),
                    ("50_50", "50/50"),
                    ("quincenal", "Quincenal"),
                    ("por_visita", "Por visita"),
                    ("fin_mensualidad", "Fin de la mensualidad"),
                    ("semestral_adelantado", "Anual · 2 pagos semestrales adelantados"),
                    ("personalizado", "Personalizado"),
                ],
                default="",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="programacion_cobro",
            field=models.CharField(
                choices=[
                    ("inicio_periodo", "Mismo día de inicio del periodo"),
                    ("cierre_periodo", "Mismo día de cierre del periodo"),
                    ("dia_fijo", "Día fijo mensual"),
                    ("rango_dias", "Rango de días"),
                    ("dos_pagos", "Dos pagos mensuales"),
                    ("despues_cierre", "Días después del cierre"),
                    ("semestral_adelantado", "Pago semestral adelantado · 6 meses"),
                    ("personalizado", "Personalizado"),
                ],
                default="inicio_periodo",
                max_length=30,
            ),
        ),
    ]
