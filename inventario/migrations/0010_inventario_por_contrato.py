from decimal import Decimal
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("contratos", "0009_gestion_quimicos_contrato"),
        ("inventario", "0009_alter_entradastock_options_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InventarioContrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stock", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12)),
                ("stock_minimo", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12)),
                ("consumo_diario_estimado", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12)),
                ("fecha_referencia_estimacion", models.DateField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("contrato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventario_en_sitio", to="contratos.contrato")),
                ("insumo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stocks_contratos", to="inventario.insumo")),
            ],
            options={
                "verbose_name": "Inventario de contrato",
                "verbose_name_plural": "Inventarios de contratos",
                "ordering": ["contrato__cliente__nombre", "insumo__nombre"],
            },
        ),
        migrations.AddConstraint(
            model_name="inventariocontrato",
            constraint=models.UniqueConstraint(fields=("contrato", "insumo"), name="uniq_inventario_contrato_insumo"),
        ),
        migrations.AlterField(
            model_name="movimientoinventario",
            name="tipo",
            field=models.CharField(
                choices=[
                    ("compra", "Compra"), ("entrada", "Entrada / ajuste +"), ("venta", "Venta"),
                    ("entrega", "Entrega a trabajador"), ("devolucion", "Devolución de trabajador"),
                    ("mantenimiento", "Consumo en mantenimiento"), ("ajuste", "Ajuste"),
                    ("reposicion_contrato", "Reposición a contrato"), ("consumo_contrato", "Consumo de contrato"),
                    ("ajuste_contrato", "Ajuste de contrato"),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="contrato",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_inventario", to="contratos.contrato"),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="stock_contrato_anterior",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name="movimientoinventario",
            name="stock_contrato_resultante",
            field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True),
        ),
    ]
