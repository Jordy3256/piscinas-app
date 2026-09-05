from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0013_jvaqua_digital_planes_mantenimiento")]
    operations = [
        migrations.AddField(
            model_name="piscinasuscriptor",
            name="origen_agua",
            field=models.CharField(choices=[("potable", "Potable / red pública"), ("pozo", "Pozo"), ("mixta", "Mixta"), ("otro", "Otro / no lo sé")], db_index=True, default="potable", max_length=20),
        ),
        migrations.AddField(
            model_name="piscinasuscriptor",
            name="antecedente_hierro",
            field=models.CharField(choices=[("no_se", "No lo sé"), ("si", "Sí / ha reaccionado al cloro"), ("no", "No detectado")], default="no_se", max_length=12),
        ),
    ]
