from decimal import Decimal
from django.db import migrations, models
import django.core.validators


def migrar_configuracion(apps, schema_editor):
    Contrato = apps.get_model("contratos", "Contrato")
    for contrato in Contrato.objects.all().iterator():
        dia_inicio = getattr(contrato.fecha_inicio, "day", 1) or 1
        contrato.periodo_dia_inicio = min(max(dia_inicio, 1), 31)
        forma = contrato.forma_pago
        if forma == "dia_fijo":
            contrato.forma_pago = "adelantado"
            contrato.programacion_cobro = "dia_fijo"
            contrato.cobro_dia_1 = contrato.dia_pago or dia_inicio
        elif forma == "adelantado":
            contrato.programacion_cobro = "inicio_periodo"
        elif forma == "50_50":
            contrato.programacion_cobro = "dos_pagos"
            contrato.cobro_dia_1 = dia_inicio
            contrato.cobro_dia_2 = min(dia_inicio + 15, 31)
            contrato.porcentaje_primer_pago = Decimal("50.00")
        elif forma == "fin_mensualidad":
            contrato.programacion_cobro = "cierre_periodo"
        else:
            contrato.programacion_cobro = "inicio_periodo"
        contrato.save(update_fields=[
            "periodo_dia_inicio", "forma_pago", "programacion_cobro",
            "cobro_dia_1", "cobro_dia_2", "porcentaje_primer_pago",
        ])


class Migration(migrations.Migration):
    dependencies = [("contratos", "0006_contrato_dia_pago")]
    operations = [
        migrations.AlterField(
            model_name="contrato", name="forma_pago",
            field=models.CharField(blank=True, choices=[
                ("adelantado", "Adelantado"), ("servicio_cumplido", "Servicio cumplido"),
                ("50_50", "50/50"), ("quincenal", "Quincenal"), ("por_visita", "Por visita"),
                ("fin_mensualidad", "Fin de la mensualidad"), ("personalizado", "Personalizado")],
                default="", max_length=30),
        ),
        migrations.AddField(model_name="contrato", name="periodo_dia_inicio", field=models.PositiveSmallIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="programacion_cobro", field=models.CharField(choices=[("inicio_periodo", "Mismo día de inicio del periodo"), ("cierre_periodo", "Mismo día de cierre del periodo"), ("dia_fijo", "Día fijo mensual"), ("rango_dias", "Rango de días"), ("dos_pagos", "Dos pagos mensuales"), ("despues_cierre", "Días después del cierre"), ("personalizado", "Personalizado")], default="inicio_periodo", max_length=30)),
        migrations.AddField(model_name="contrato", name="cobro_mes_desfase", field=models.PositiveSmallIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)])),
        migrations.AddField(model_name="contrato", name="cobro_dia_1", field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="cobro_dia_2", field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="cobro_rango_desde", field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="cobro_rango_hasta", field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="cobro_dias_despues_cierre", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="contrato", name="porcentaje_primer_pago", field=models.DecimalField(decimal_places=2, default=Decimal("50.00"), max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal("0.01")), django.core.validators.MaxValueValidator(Decimal("99.99"))])),
        migrations.AddField(model_name="contrato", name="programacion_cobro_personalizada", field=models.CharField(blank=True, default="", max_length=200)),
        migrations.AddField(model_name="contrato", name="requiere_factura", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="contrato", name="momento_facturacion", field=models.CharField(blank=True, choices=[("antes_inicio", "Antes de iniciar el periodo"), ("inicio_periodo", "Al iniciar el periodo"), ("cierre_periodo", "Al finalizar el periodo"), ("dia_fijo", "Día fijo del mes"), ("antes_cobro", "Días antes del cobro"), ("personalizado", "Personalizado")], default="", max_length=30)),
        migrations.AddField(model_name="contrato", name="facturacion_dia", field=models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)])),
        migrations.AddField(model_name="contrato", name="facturacion_dias_antes", field=models.PositiveSmallIntegerField(default=0)),
        migrations.AddField(model_name="contrato", name="notificar_facturacion", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="contrato", name="notificacion_factura_dias_antes", field=models.PositiveSmallIntegerField(default=1)),
        migrations.AddField(model_name="contrato", name="observaciones_facturacion", field=models.TextField(blank=True, default="")),
        migrations.RunPython(migrar_configuracion, migrations.RunPython.noop),
    ]
