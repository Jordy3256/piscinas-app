from decimal import Decimal

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("mantenimientos", "0008_mantenimiento_observaciones_rapidas"),
        ("inventario", "0006_inventario_inteligente"),
        ("trabajadores", "0004_pago_fin_periodo_servicio"),
    ]

    operations = [
        migrations.AlterField(model_name="usoinsumo", name="insumo", field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="inventario.insumo")),
        migrations.AlterField(model_name="usoinsumo", name="cantidad", field=models.DecimalField(decimal_places=3, help_text="Cantidad convertida a la unidad base del producto.", max_digits=12)),
        migrations.AddField(model_name="usoinsumo", name="trabajador", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="usos_insumos", to="trabajadores.trabajador")),
        migrations.AddField(model_name="usoinsumo", name="cantidad_ingresada", field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
        migrations.AddField(model_name="usoinsumo", name="unidad_registro", field=models.CharField(choices=[("g", "Gramos"), ("kg", "Kilogramos"), ("unidad", "Unidades")], default="kg", max_length=10)),
        migrations.AddField(model_name="usoinsumo", name="costo_unitario", field=models.DecimalField(decimal_places=4, default=0, max_digits=12)),
        migrations.AddField(model_name="usoinsumo", name="costo_total", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
    ]
