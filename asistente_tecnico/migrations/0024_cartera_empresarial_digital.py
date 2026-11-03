from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0023_alter_solicitudsuscripciondigital_plan")]
    operations = [
        migrations.CreateModel(name="CobroPiscinaDigital", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("periodo", models.DateField(help_text="Primer día del mes de servicio")),
            ("vencimiento", models.DateField(db_index=True)),
            ("importe", models.DecimalField(max_digits=10, decimal_places=2)),
            ("observaciones", models.CharField(blank=True, default="", max_length=255)),
            ("creado_en", models.DateTimeField(auto_now_add=True)),
            ("piscina", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cobros_digitales", to="asistente_tecnico.piscinasuscriptor")),
        ], options={"ordering": ["vencimiento", "piscina__nombre"], "verbose_name": "Cobro AQUO360 Empresarial", "verbose_name_plural": "Cobros AQUO360 Empresarial"}),
        migrations.CreateModel(name="PagoCobroDigital", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("importe", models.DecimalField(max_digits=10, decimal_places=2)),
            ("fecha_pago", models.DateField(default=django.utils.timezone.localdate)),
            ("nota", models.CharField(blank=True, default="", max_length=255)),
            ("creado_en", models.DateTimeField(auto_now_add=True)),
            ("cobro", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pagos", to="asistente_tecnico.cobropiscinadigital")),
        ], options={"ordering": ["-fecha_pago", "-id"], "verbose_name": "Pago recibido AQUO360", "verbose_name_plural": "Pagos recibidos AQUO360"}),
        migrations.AddField(model_name="notificaciondigital", name="cobro", field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="notificaciones", to="asistente_tecnico.cobropiscinadigital")),
        migrations.AlterField(model_name="notificaciondigital", name="tipo", field=models.CharField(choices=[("plan_creado", "Plan creado"), ("visita_hoy", "Visita de hoy"), ("recordatorio", "Recordatorio"), ("cobro_proximo", "Cobro próximo"), ("cobro_hoy", "Cobro de hoy"), ("cobro_vencido", "Cobro vencido")], db_index=True, default="recordatorio", max_length=20)),
        migrations.AddConstraint(model_name="cobropiscinadigital", constraint=models.UniqueConstraint(fields=("piscina", "periodo"), name="uq_aquo_cobro_piscina_periodo")),
        migrations.AddConstraint(model_name="notificaciondigital", constraint=models.UniqueConstraint(fields=("suscriptor", "cobro", "tipo"), name="uq_aquo_cobro_aviso_tipo")),
    ]
