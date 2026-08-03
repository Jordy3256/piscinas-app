from django.conf import settings
from django.db import migrations, models
import django.core.validators
import django.db.models.deletion
import datetime
from decimal import Decimal

class Migration(migrations.Migration):
    dependencies=[("finanzas","0009_sincronizar_contratos_inactivos"),("trabajadores","0001_initial"),migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations=[
      migrations.CreateModel(name="LotePagoTrabajador", fields=[
        ("id",models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name="ID")),
        ("periodo_anio",models.PositiveIntegerField(db_index=True)),("periodo_mes",models.PositiveIntegerField(db_index=True)),
        ("monto",models.DecimalField(decimal_places=2,max_digits=12,validators=[django.core.validators.MinValueValidator(Decimal("0.01"))])),
        ("fecha",models.DateField(db_index=True,default=datetime.date.today)),
        ("metodo_pago",models.CharField(choices=[("efectivo","Efectivo"),("transferencia","Transferencia"),("tarjeta","Tarjeta"),("deposito","Depósito"),("cheque","Cheque"),("otro","Otro")],default="transferencia",max_length=20)),
        ("referencia",models.CharField(blank=True,default="",max_length=120)),
        ("comprobante",models.FileField(blank=True,null=True,upload_to="finanzas/pagos_trabajadores_consolidados/%Y/%m/")),
        ("observaciones",models.TextField(blank=True,default="")),("activo",models.BooleanField(db_index=True,default=True)),("creado_en",models.DateTimeField(auto_now_add=True)),
        ("creado_por",models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="lotes_pago_trabajador_creados",to=settings.AUTH_USER_MODEL)),
        ("egreso",models.OneToOneField(blank=True,null=True,on_delete=django.db.models.deletion.SET_NULL,related_name="lote_pago_trabajador",to="finanzas.egreso")),
        ("trabajador",models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name="lotes_pago",to="trabajadores.trabajador")),
      ], options={"verbose_name":"Pago consolidado a trabajador","verbose_name_plural":"Pagos consolidados a trabajadores","ordering":["-fecha","-id"]}),
      migrations.AddField(model_name="pagotrabajador",name="lote",field=models.ForeignKey(blank=True,null=True,on_delete=django.db.models.deletion.PROTECT,related_name="distribuciones",to="finanzas.lotepagotrabajador")),
    ]
