from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import datetime
from decimal import Decimal


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finanzas", "0005_panel_financiero_v2"),
    ]

    operations = [
        migrations.AlterField(
            model_name="factura",
            name="estado",
            field=models.CharField(
                choices=[
                    ("pendiente", "Pendiente"),
                    ("parcial", "Parcial"),
                    ("pagada", "Pagada"),
                    ("vencida", "Vencida"),
                    ("anulada", "Anulada"),
                ],
                default="pendiente",
                max_length=10,
            ),
        ),
        migrations.CreateModel(
            name="PagoFactura",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("monto", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
                ("fecha", models.DateField(db_index=True, default=datetime.date.today)),
                ("metodo_pago", models.CharField(choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia"), ("tarjeta", "Tarjeta"), ("deposito", "Depósito"), ("cheque", "Cheque"), ("otro", "Otro")], default="transferencia", max_length=20)),
                ("referencia", models.CharField(blank=True, default="", max_length=120)),
                ("comprobante", models.FileField(blank=True, null=True, upload_to="finanzas/pagos_facturas/%Y/%m/")),
                ("observaciones", models.TextField(blank=True, default="")),
                ("activo", models.BooleanField(db_index=True, default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pagos_factura_creados", to=settings.AUTH_USER_MODEL)),
                ("factura", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="pagos", to="finanzas.factura")),
                ("ingreso", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pago_factura", to="finanzas.ingreso")),
            ],
            options={
                "verbose_name": "Pago de factura",
                "verbose_name_plural": "Pagos de facturas",
                "ordering": ["-fecha", "-id"],
            },
        ),
    ]
