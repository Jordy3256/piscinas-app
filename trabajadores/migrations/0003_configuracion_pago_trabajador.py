from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [("trabajadores", "0002_alter_trabajador_options")]
    operations = [
        migrations.AddField(model_name="trabajador", name="forma_pago_nomina", field=models.CharField(choices=[("fin_mes", "Al finalizar el mes"), ("adelantado", "Por adelantado"), ("semanal", "Semanal"), ("quincenal", "Quincenal"), ("por_visita", "Por visita"), ("por_contrato", "Por contrato"), ("personalizado", "Personalizado")], default="fin_mes", max_length=20)),
        migrations.AddField(model_name="trabajador", name="programacion_pago_nomina", field=models.CharField(choices=[("fecha_contratos", "Mismas fechas de cobro de los contratos"), ("dia_fijo", "Día fijo mensual"), ("rango", "Rango de días"), ("personalizado", "Personalizado")], default="fecha_contratos", max_length=25)),
        migrations.AddField(model_name="trabajador", name="modalidad_pago_nomina", field=models.CharField(choices=[("unico", "Un solo pago consolidado"), ("dos_pagos", "Dos pagos"), ("parciales", "Pagos parciales"), ("personalizado", "Personalizado")], default="unico", max_length=20)),
        migrations.AddField(model_name="trabajador", name="dia_pago_nomina", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="trabajador", name="dia_pago_desde", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="trabajador", name="dia_pago_hasta", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="trabajador", name="segundo_dia_pago", field=models.PositiveSmallIntegerField(blank=True, null=True)),
        migrations.AddField(model_name="trabajador", name="observaciones_pago", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="trabajador", name="fecha_ingreso", field=models.DateField(blank=True, null=True)),
    ]
