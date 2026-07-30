from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def marcar_existentes_pagados(apps, schema_editor):
    Ingreso = apps.get_model("finanzas", "Ingreso")
    Egreso = apps.get_model("finanzas", "Egreso")
    for item in Ingreso.objects.all().iterator():
        item.monto_pagado = item.total or Decimal("0.00")
        item.estado = "pagado"
        item.fecha_cobro = item.fecha
        item.save(update_fields=["monto_pagado", "estado", "fecha_cobro"])
    for item in Egreso.objects.all().iterator():
        item.monto_pagado = item.total or Decimal("0.00")
        item.estado = "pagado"
        item.save(update_fields=["monto_pagado", "estado"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finanzas", "0004_factura_facturaitem_and_more"),
    ]

    operations = [
        migrations.AddField(model_name="ingreso", name="actualizado_en", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="ingreso", name="ciudad", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="ingreso", name="comprobante", field=models.FileField(blank=True, null=True, upload_to="finanzas/comprobantes/%Y/%m/")),
        migrations.AddField(model_name="ingreso", name="creado_en", field=models.DateTimeField(auto_now_add=True, default="2026-07-29T00:00:00Z"), preserve_default=False),
        migrations.AddField(model_name="ingreso", name="creado_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ingreso_creados", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="ingreso", name="estado", field=models.CharField(choices=[("pendiente", "Pendiente"), ("parcial", "Parcial"), ("pagado", "Pagado"), ("vencido", "Vencido"), ("anulado", "Anulado")], db_index=True, default="pagado", max_length=12)),
        migrations.AddField(model_name="ingreso", name="fecha_cobro", field=models.DateField(blank=True, null=True)),
        migrations.AddField(model_name="ingreso", name="fecha_vencimiento", field=models.DateField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="ingreso", name="metodo_pago", field=models.CharField(blank=True, choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia"), ("tarjeta", "Tarjeta"), ("deposito", "Depósito"), ("cheque", "Cheque"), ("otro", "Otro")], default="", max_length=20)),
        migrations.AddField(model_name="ingreso", name="monto_pagado", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="ingreso", name="observaciones", field=models.TextField(blank=True, default="")),
        migrations.AlterField(model_name="ingreso", name="fecha", field=models.DateField(db_index=True, default=date.today)),

        migrations.AddField(model_name="egreso", name="actualizado_en", field=models.DateTimeField(auto_now=True)),
        migrations.AddField(model_name="egreso", name="aprobado", field=models.BooleanField(db_index=True, default=True)),
        migrations.AddField(model_name="egreso", name="ciudad_proyecto", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="egreso", name="comprobante", field=models.FileField(blank=True, null=True, upload_to="finanzas/comprobantes/%Y/%m/")),
        migrations.AddField(model_name="egreso", name="creado_en", field=models.DateTimeField(auto_now_add=True, default="2026-07-29T00:00:00Z"), preserve_default=False),
        migrations.AddField(model_name="egreso", name="creado_por", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="egreso_creados", to=settings.AUTH_USER_MODEL)),
        migrations.AddField(model_name="egreso", name="estado", field=models.CharField(choices=[("pendiente", "Pendiente"), ("parcial", "Parcial"), ("pagado", "Pagado"), ("vencido", "Vencido"), ("anulado", "Anulado")], db_index=True, default="pagado", max_length=12)),
        migrations.AddField(model_name="egreso", name="fecha_vencimiento", field=models.DateField(blank=True, db_index=True, null=True)),
        migrations.AddField(model_name="egreso", name="metodo_pago", field=models.CharField(blank=True, choices=[("efectivo", "Efectivo"), ("transferencia", "Transferencia"), ("tarjeta", "Tarjeta"), ("deposito", "Depósito"), ("cheque", "Cheque"), ("otro", "Otro")], default="", max_length=20)),
        migrations.AddField(model_name="egreso", name="monto_pagado", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.AddField(model_name="egreso", name="observaciones", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="egreso", name="proveedor", field=models.CharField(blank=True, default="", max_length=150)),
        migrations.AlterField(model_name="egreso", name="categoria", field=models.CharField(blank=True, choices=[("quimicos", "Químicos"), ("tecnicos", "Sueldos y pagos a técnicos"), ("transporte", "Transporte"), ("alimentacion", "Alimentación"), ("hospedaje", "Hospedaje"), ("materiales", "Materiales"), ("herramientas", "Herramientas"), ("reparaciones", "Reparaciones"), ("publicidad", "Publicidad"), ("servicios", "Servicios"), ("administracion", "Administración"), ("otros", "Otros gastos")], db_index=True, default="otros", max_length=30)),
        migrations.AlterField(model_name="egreso", name="fecha", field=models.DateField(db_index=True, default=date.today)),
        migrations.AlterField(model_name="egreso", name="total", field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        migrations.RunPython(marcar_existentes_pagados, migrations.RunPython.noop),
    ]
