from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0026_push_digital_aislado")]
    operations = [
        migrations.AlterField(
            model_name="notificaciondigital", name="tipo",
            field=models.CharField(max_length=20, default="recordatorio", db_index=True,
                choices=[("plan_creado", "Plan creado"), ("visita_hoy", "Visita de hoy"),
                    ("recordatorio", "Recordatorio"), ("cobro_proximo", "Cobro próximo"),
                    ("cobro_hoy", "Cobro de hoy"), ("cobro_vencido", "Cobro vencido"),
                    ("suscripcion_proxima", "Suscripción por vencer")]),
        ),
        migrations.AddConstraint(
            model_name="notificaciondigital",
            constraint=models.UniqueConstraint(
                fields=["suscriptor", "tipo", "programada_para"],
                condition=models.Q(tipo="suscripcion_proxima"),
                name="uq_aquo_aviso_renovacion_dia",
            ),
        ),
    ]
