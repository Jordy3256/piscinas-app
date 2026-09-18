from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contratos", "0018_pago_por_visita_sincronizado")]

    operations = [
        # Solo se amplía estructura/metadata. No existe RunPython ni conversión
        # de datos: contratos, fechas, cartera y pagos históricos quedan intactos.
        migrations.AlterField(
            model_name="contrato",
            name="forma_pago",
            field=models.CharField(
                blank=True,
                default="",
                max_length=30,
                choices=[
                    ("adelantado", "Mes Adelantado"),
                    ("servicio_cumplido", "Mes Cumplido"),
                    ("50_50", "Inicio 50% - 50% Final"),
                    ("por_visita", "Por visita"),
                    ("anual", "Anual"),
                    ("quincenal", "Quincenal (anterior)"),
                    ("fin_mensualidad", "Fin de la mensualidad (anterior)"),
                    ("semestral_adelantado", "Anual · 2 pagos semestrales adelantados (anterior)"),
                    ("personalizado", "Personalizado (anterior)"),
                ],
            ),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="programacion_cobro",
            field=models.CharField(
                default="inicio_periodo",
                max_length=30,
                choices=[
                    ("inicio_periodo", "Mismo día de inicio del periodo"),
                    ("cierre_periodo", "Mismo día de cierre del periodo"),
                    ("dia_fijo", "Día fijo mensual"),
                    ("rango_dias", "Rango de días"),
                    ("despues_cierre", "Días máximos después del cierre"),
                    ("por_visita", "Por visita"),
                    ("adelanto_mensualidades", "Adelanto de X mensualidades"),
                    ("dos_pagos", "Dos pagos mensuales (anterior)"),
                    ("semestral_adelantado", "Pago semestral adelantado · 6 meses (anterior)"),
                    ("personalizado", "Personalizado (anterior)"),
                ],
            ),
        ),
        migrations.AddField(
            model_name="contrato",
            name="cobro_meses_adelantados",
            field=models.PositiveSmallIntegerField(default=1, help_text="Cantidad de mensualidades que se cobran juntas por adelantado.", validators=[MinValueValidator(1), MaxValueValidator(12)]),
        ),
        migrations.AddField(
            model_name="reactivacioncontrato",
            name="cobro_meses_adelantados",
            field=models.PositiveSmallIntegerField(default=1, help_text="Cantidad de mensualidades que se cobran juntas por adelantado.", validators=[MinValueValidator(1), MaxValueValidator(12)]),
        ),
    ]
