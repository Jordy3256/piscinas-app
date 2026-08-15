from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    dependencies = [("asistente_tecnico", "0011_academia_operacion_y_diagnostico_v4"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="PerfilSuscriptor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("estado", models.CharField(choices=[("prueba","Prueba"),("activo","Activo"),("pausado","Pausado"),("vencido","Vencido")], db_index=True, default="prueba", max_length=20)),
                ("plan", models.CharField(choices=[("digital","JVAQUA Digital")], default="digital", max_length=30)),
                ("inicio", models.DateField(default=django.utils.timezone.localdate)),
                ("prueba_hasta", models.DateField(blank=True, null=True)),
                ("acceso_hasta", models.DateField(blank=True, null=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="perfil_suscriptor", to=settings.AUTH_USER_MODEL)),
            ],
            options={"verbose_name":"Suscriptor JVAQUA Digital","verbose_name_plural":"Suscriptores JVAQUA Digital"},
        ),
        migrations.CreateModel(
            name="PiscinaSuscriptor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(default="Mi piscina", max_length=100)),
                ("tipo_piscina", models.CharField(choices=[("residencial","Residencial"),("condominio","Condominio / urbanización"),("hotel","Hotel / hostería"),("publica","Piscina pública / alto uso")], default="residencial", max_length=30)),
                ("largo_m", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("ancho_m", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("profundidad_m", models.DecimalField(blank=True, decimal_places=2, max_digits=7, null=True)),
                ("volumen_m3", models.DecimalField(decimal_places=2, max_digits=9)),
                ("tipo_filtro", models.CharField(choices=[("arena","Filtro de arena"),("cartucho","Filtro de cartucho"),("otro","Otro / no lo sé")], default="arena", max_length=20)),
                ("desinfeccion", models.CharField(choices=[("cloro","Cloro"),("sal","Cloración salina"),("otro","Otro / no lo sé")], default="cloro", max_length=20)),
                ("notas", models.TextField(blank=True, default="")),
                ("principal", models.BooleanField(db_index=True, default=False)),
                ("activa", models.BooleanField(db_index=True, default=True)),
                ("creado_en", models.DateTimeField(auto_now_add=True)),
                ("actualizado_en", models.DateTimeField(auto_now=True)),
                ("suscriptor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="piscinas", to="asistente_tecnico.perfilsuscriptor")),
            ],
            options={"verbose_name":"Piscina de suscriptor","verbose_name_plural":"Piscinas de suscriptores","ordering":["-principal","nombre"]},
        ),
    ]
