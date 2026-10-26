from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("ordenes_trabajo", "0002_rename_ordenes_tra_fecha_2fd66d_idx_ordenes_tra_fecha_e29325_idx_and_more"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="ordentrabajo", name="resultado_reportado", field=models.CharField(max_length=20, blank=True, default="", choices=[("realizado", "Realizado"), ("no_realizado", "No realizado")])),
        migrations.AddField(model_name="ordentrabajo", name="pendiente_revision", field=models.BooleanField(default=False, db_index=True)),
        migrations.AddField(model_name="ordentrabajo", name="revision_admin_en", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="ordentrabajo", name="revisado_por", field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordenes_revisadas")),
        migrations.AddField(model_name="ordentrabajo", name="cobro_reportado", field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="ordentrabajo", name="cobro_metodo", field=models.CharField(max_length=30, blank=True, default="")),
        migrations.AddField(model_name="ordentrabajo", name="cobro_comprobante", field=models.FileField(upload_to="ordenes_trabajo/comprobantes/", null=True, blank=True)),
        migrations.AddField(model_name="ordentrabajo", name="cobro_observacion", field=models.TextField(blank=True, default="")),
        migrations.AddField(model_name="ordentrabajo", name="cobro_verificado", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="ordentrabajo", name="cobro_confirmado", field=models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)),
        migrations.AddField(model_name="ordentrabajo", name="cobro_confirmado_metodo", field=models.CharField(max_length=30, blank=True, default="")),
        migrations.AddField(model_name="ordentrabajo", name="cobro_confirmado_en", field=models.DateTimeField(null=True, blank=True)),
        migrations.AddField(model_name="ordentrabajo", name="cobro_confirmado_por", field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordenes_cobro_verificado")),
        migrations.AddField(model_name="ordentrabajo", name="observaciones_revision", field=models.TextField(blank=True, default="")),
        migrations.AlterField(model_name="ordentrabajo", name="estado", field=models.CharField(max_length=20, default="pendiente", db_index=True, choices=[("pendiente", "Pendiente"), ("en_proceso", "En proceso"), ("completada", "Completada"), ("cancelada", "Cancelada"), ("no_completada", "No completada")])),
    ]
