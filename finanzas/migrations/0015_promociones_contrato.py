from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("finanzas", "0014_alter_facturaitem_options_alter_ingreso_options_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="PromocionContrato",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=120)), ("motivo", models.TextField()),
                ("tipo", models.CharField(choices=[("porcentaje","Porcentaje de descuento"),("valor_fijo","Valor fijo de descuento"),("gratis","Mes gratis / 100%"),("valor_especial","Valor especial a cobrar")], max_length=20)),
                ("valor", models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ("anio_inicio", models.PositiveIntegerField()), ("mes_inicio", models.PositiveSmallIntegerField()),
                ("anio_fin", models.PositiveIntegerField()), ("mes_fin", models.PositiveSmallIntegerField()),
                ("activa", models.BooleanField(default=True)), ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("contrato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="promociones", to="contratos.contrato")),
                ("creado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="promociones_contrato_creadas", to=settings.AUTH_USER_MODEL)),
            ], options={"ordering":["-anio_inicio","-mes_inicio","-id"]}),
        migrations.AddField(model_name="factura", name="valor_contractual", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="factura", name="descuento_promocion", field=models.DecimalField(decimal_places=2, default=0, max_digits=12)),
        migrations.AddField(model_name="factura", name="promocion_nombre", field=models.CharField(blank=True, default="", max_length=120)),
        migrations.AddField(model_name="factura", name="promocion", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="facturas", to="finanzas.promocioncontrato")),
        migrations.AlterField(model_name="factura", name="estado", field=models.CharField(choices=[("pendiente","Pendiente"),("parcial","Parcial"),("pagada","Pagada"),("vencida","Vencida"),("anulada","Anulada"),("promocion","Cubierto por promoción")], default="pendiente", max_length=10)),
    ]
