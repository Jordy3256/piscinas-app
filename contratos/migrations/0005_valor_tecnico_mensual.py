from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies=[("contratos","0004_programacion_automatica")]
    operations=[migrations.AddField(model_name="contrato",name="valor_tecnico_mensual",field=models.DecimalField(decimal_places=2,default=0,help_text="Valor mensual acordado con el técnico por este contrato.",max_digits=10))]
