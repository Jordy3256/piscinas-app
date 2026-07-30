from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("contratos", "0005_valor_tecnico_mensual")]
    operations = [
        migrations.AddField(
            model_name="contrato",
            name="dia_pago",
            field=models.PositiveSmallIntegerField(blank=True, help_text="Día acordado para el cobro mensual (1 a 31).", null=True),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="forma_pago",
            field=models.CharField(blank=True, choices=[("adelantado", "Adelantado"), ("50_50", "50/50"), ("por_visita", "Por visita"), ("fin_mensualidad", "Fin de la mensualidad"), ("dia_fijo", "Día fijo mensual"), ("personalizado", "Personalizado")], default="", max_length=30),
        ),
    ]
