from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def copiar_fecha_inicio_original(apps, schema_editor):
    Contrato = apps.get_model("contratos", "Contrato")
    Contrato.objects.filter(fecha_inicio_original__isnull=True).update(fecha_inicio_original=models.F("fecha_inicio"))


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0013_ubicacion_por_contrato"),
        ("trabajadores", "0005_ciudades_trabajador"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.AddField(
            model_name="contrato", name="fecha_inicio_original",
            field=models.DateField(blank=True, db_index=True, null=True),
        ),
        migrations.RunPython(copiar_fecha_inicio_original, migrations.RunPython.noop),
        migrations.CreateModel(
            name="ReactivacionContrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("fecha_reactivacion", models.DateField(db_index=True)),
                ("registrada_en", models.DateTimeField(auto_now_add=True)),
                ("fecha_baja_anterior", models.DateField(blank=True, null=True)),
                ("motivo_baja_anterior", models.CharField(blank=True, default="", max_length=30)),
                ("fecha_inicio_anterior", models.DateField(blank=True, null=True)),
                ("fecha_inicio", models.DateField()),
                ("frecuencia", models.CharField(blank=True, default="", max_length=30)),
                ("frecuencia_personalizada", models.CharField(blank=True, default="", max_length=150)),
                ("dias_visita", models.JSONField(blank=True, default=list)),
                ("forma_pago", models.CharField(blank=True, default="", max_length=30)),
                ("forma_pago_personalizada", models.CharField(blank=True, default="", max_length=150)),
                ("periodo_dia_inicio", models.PositiveSmallIntegerField(default=1)),
                ("programacion_cobro", models.CharField(blank=True, default="", max_length=30)),
                ("cobro_mes_desfase", models.PositiveSmallIntegerField(default=0)),
                ("cobro_dia_1", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("cobro_dia_2", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("cobro_rango_desde", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("cobro_rango_hasta", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("cobro_dias_despues_cierre", models.PositiveSmallIntegerField(default=0)),
                ("porcentaje_primer_pago", models.DecimalField(decimal_places=2, default=Decimal("50.00"), max_digits=5)),
                ("programacion_cobro_personalizada", models.CharField(blank=True, default="", max_length=200)),
                ("precio_mensual", models.DecimalField(decimal_places=2, max_digits=10)),
                ("valor_tecnico_mensual", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("contrato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reactivaciones", to="contratos.contrato")),
                ("registrada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("tecnico_designado", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="reactivaciones_contrato", to="trabajadores.trabajador")),
            ],
            options={"verbose_name":"Reactivación de contrato","verbose_name_plural":"Reactivaciones de contratos","ordering":["-fecha_reactivacion","-registrada_en","-id"]},
        ),
    ]
