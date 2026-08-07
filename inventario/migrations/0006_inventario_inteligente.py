from decimal import Decimal

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0005_alter_insumo_options_insumo_costo_and_more"),
        ("trabajadores", "0004_pago_fin_periodo_servicio"),
        ("mantenimientos", "0008_mantenimiento_observaciones_rapidas"),
        ("finanzas", "0013_periodo_servicio_nomina"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(model_name="insumo", name="activo", field=models.BooleanField(db_index=True, default=True)),
        migrations.AddField(model_name="insumo", name="categoria", field=models.CharField(choices=[("quimicos", "Químicos"), ("repuestos", "Repuestos"), ("herramientas", "Herramientas"), ("equipos", "Equipos"), ("construccion", "Materiales de construcción"), ("otros", "Otros")], db_index=True, default="quimicos", max_length=20)),
        migrations.AddField(model_name="insumo", name="codigo", field=models.CharField(blank=True, db_index=True, default="", max_length=40)),
        migrations.AddField(model_name="insumo", name="puede_asignarse_trabajador", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="insumo", name="puede_construccion", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="insumo", name="puede_mantenimiento", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="insumo", name="puede_venderse", field=models.BooleanField(default=True)),
        migrations.AddField(model_name="insumo", name="stock_maximo", field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
        migrations.AddField(model_name="insumo", name="unidad_base", field=models.CharField(choices=[("kg", "Kilogramos"), ("unidad", "Unidades")], default="kg", max_length=10)),
        migrations.AlterField(model_name="insumo", name="stock", field=models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12)),
        migrations.AlterField(model_name="insumo", name="stock_minimo", field=models.DecimalField(decimal_places=3, default=Decimal("5.000"), max_digits=12)),
        migrations.AlterField(model_name="insumo", name="precio", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), help_text="Precio de venta por unidad base.", max_digits=12)),
        migrations.AlterField(model_name="insumo", name="costo", field=models.DecimalField(decimal_places=4, default=Decimal("0.0000"), help_text="Costo promedio por unidad base.", max_digits=12)),
        migrations.CreateModel(
            name="PresentacionInsumo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=80)),
                ("cantidad_base", models.DecimalField(decimal_places=3, help_text="Cantidad equivalente en la unidad base del producto.", max_digits=12)),
                ("precio_venta", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("activa", models.BooleanField(default=True)),
                ("insumo", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="presentaciones", to="inventario.insumo")),
            ],
            options={"verbose_name": "Presentación de insumo", "verbose_name_plural": "Presentaciones de insumos", "ordering": ["insumo__nombre", "cantidad_base"]},
        ),
        migrations.CreateModel(
            name="InventarioTrabajador",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("stock", models.DecimalField(decimal_places=3, default=Decimal("0.000"), max_digits=12)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("insumo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="stocks_trabajadores", to="inventario.insumo")),
                ("trabajador", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventario_asignado", to="trabajadores.trabajador")),
            ],
            options={"verbose_name": "Inventario de trabajador", "verbose_name_plural": "Inventarios de trabajadores", "ordering": ["trabajador__user__username", "insumo__nombre"]},
        ),
        migrations.AddConstraint(model_name="inventariotrabajador", constraint=models.UniqueConstraint(fields=("trabajador", "insumo"), name="uniq_inventario_trabajador_insumo")),
        migrations.AlterField(model_name="ventainsumo", name="cantidad", field=models.DecimalField(decimal_places=3, max_digits=12)),
        migrations.AlterField(model_name="ventainsumo", name="precio_unitario", field=models.DecimalField(decimal_places=2, max_digits=12)),
        migrations.AlterField(model_name="ventainsumo", name="costo_unitario", field=models.DecimalField(decimal_places=4, default=0, max_digits=12)),
        migrations.AlterField(model_name="ventainsumo", name="total", field=models.DecimalField(decimal_places=2, max_digits=12)),
        migrations.AlterField(model_name="ventainsumo", name="ganancia", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="ventainsumo", name="unidad_registro", field=models.CharField(default="base", max_length=15)),
        migrations.AddField(model_name="ventainsumo", name="presentacion", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ventas", to="inventario.presentacioninsumo")),
        migrations.AlterField(model_name="entradastock", name="cantidad", field=models.DecimalField(decimal_places=3, max_digits=12)),
        migrations.AlterField(model_name="movimientoinventario", name="cantidad", field=models.DecimalField(decimal_places=3, max_digits=12)),
        migrations.AlterField(model_name="movimientoinventario", name="stock_anterior", field=models.DecimalField(decimal_places=3, default=0, max_digits=12)),
        migrations.AlterField(model_name="movimientoinventario", name="stock_resultante", field=models.DecimalField(decimal_places=3, default=0, max_digits=12)),
        migrations.AlterField(model_name="movimientoinventario", name="tipo", field=models.CharField(choices=[("compra", "Compra"), ("entrada", "Entrada / ajuste +"), ("venta", "Venta"), ("entrega", "Entrega a trabajador"), ("devolucion", "Devolución de trabajador"), ("mantenimiento", "Consumo en mantenimiento"), ("ajuste", "Ajuste")], db_index=True, max_length=20)),
        migrations.AddField(model_name="movimientoinventario", name="costo_unitario", field=models.DecimalField(decimal_places=4, default=0, max_digits=12)),
        migrations.AddField(model_name="movimientoinventario", name="total_costo", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="movimientoinventario", name="stock_trabajador_anterior", field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
        migrations.AddField(model_name="movimientoinventario", name="stock_trabajador_resultante", field=models.DecimalField(blank=True, decimal_places=3, max_digits=12, null=True)),
        migrations.AddField(model_name="movimientoinventario", name="trabajador", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_inventario", to="trabajadores.trabajador")),
        migrations.AddField(model_name="movimientoinventario", name="mantenimiento", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_inventario", to="mantenimientos.mantenimiento")),
        migrations.AddField(model_name="movimientoinventario", name="usuario", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="movimientos_inventario_registrados", to=settings.AUTH_USER_MODEL)),
        migrations.CreateModel(
            name="CompraInsumo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cantidad", models.DecimalField(decimal_places=3, max_digits=12)),
                ("costo_unitario", models.DecimalField(decimal_places=4, max_digits=12)),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("proveedor", models.CharField(blank=True, default="", max_length=150)),
                ("observacion", models.CharField(blank=True, default="", max_length=255)),
                ("fecha", models.DateField(auto_now_add=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("egreso", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="compra_inventario", to="finanzas.egreso")),
                ("insumo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="compras", to="inventario.insumo")),
            ],
            options={"verbose_name": "Compra de inventario", "verbose_name_plural": "Compras de inventario", "ordering": ["-fecha", "-id"]},
        ),
    ]
