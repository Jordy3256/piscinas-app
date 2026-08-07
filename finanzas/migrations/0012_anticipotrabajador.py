from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import datetime
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0011_facturas_por_cuotas_y_periodos"), migrations.swappable_dependency(settings.AUTH_USER_MODEL), ("trabajadores", "0003_configuracion_pago_trabajador")]
    operations = [migrations.CreateModel(name="AnticipoTrabajador", fields=[
        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
        ("monto", models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
        ("fecha", models.DateField(db_index=True, default=datetime.date.today)),
        ("periodo_anio", models.PositiveIntegerField(db_index=True)),
        ("periodo_mes", models.PositiveIntegerField(db_index=True)),
        ("descontado", models.BooleanField(db_index=True, default=False)),
        ("monto_descontado", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
        ("fecha_descuento", models.DateField(blank=True, null=True)),
        ("observaciones", models.TextField(blank=True, default="")),
        ("creado_en", models.DateTimeField(auto_now_add=True)),
        ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anticipos_trabajador_creados", to=settings.AUTH_USER_MODEL)),
        ("egreso", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="anticipo_trabajador", to="finanzas.egreso")),
        ("trabajador", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="anticipos", to="trabajadores.trabajador")),
    ], options={"verbose_name":"Anticipo a trabajador", "verbose_name_plural":"Anticipos a trabajadores", "ordering":["-fecha","-id"]})]
