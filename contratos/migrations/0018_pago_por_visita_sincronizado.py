from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0017_vigencia_renovacion_contrato"),
    ]

    operations = [
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
                    ("por_visita", "Por visita"),
                    ("semestral_adelantado", "Pago semestral adelantado · 6 meses"),
                    ("personalizado", "Personalizado"),
                ],
                default="inicio_periodo",
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="momento_facturacion",
            field=models.CharField(
                blank=True,
                choices=[
                    ("antes_inicio", "Antes de iniciar el periodo"),
                    ("inicio_periodo", "Al iniciar el periodo"),
                    ("cierre_periodo", "Al finalizar el periodo"),
                    ("dia_fijo", "Día fijo del mes"),
                    ("antes_cobro", "Días antes del cobro"),
                    ("por_visita", "Por visita"),
                    ("personalizado", "Personalizado"),
                ],
                default="",
                max_length=30,
            ),
        ),
    ]
