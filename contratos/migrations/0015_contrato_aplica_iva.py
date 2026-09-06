from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("contratos", "0014_reactivacioncontrato"),
    ]

    operations = [
        migrations.AddField(
            model_name="contrato",
            name="aplica_iva",
            field=models.BooleanField(
                default=False,
                help_text="Si aplica, se agrega automáticamente IVA del 15% al valor que paga el cliente.",
            ),
        ),
        migrations.AlterField(
            model_name="contrato",
            name="precio_mensual",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Valor base mensual del contrato antes de IVA.",
                max_digits=10,
            ),
        ),
    ]
