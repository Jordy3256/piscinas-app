from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0030_experiencia_aquo")]
    operations = [migrations.CreateModel(name="ConsumoImagenAquo", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("cantidad", models.PositiveSmallIntegerField(default=1)), ("creado_en", models.DateTimeField(auto_now_add=True, db_index=True)), ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="consumos_imagen_aquo", to="asistente_tecnico.perfilsuscriptor"))], options={"indexes": [models.Index(fields=["suscriptor", "creado_en"], name="aquo_fotos_periodo_idx")]})]
