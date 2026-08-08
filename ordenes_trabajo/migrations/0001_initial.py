from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def crear_tipos(apps, schema_editor):
    Tipo = apps.get_model("ordenes_trabajo", "TipoOrdenTrabajo")
    datos = [
        ("Mantenimiento extraordinario", "🟨", "warning", 10),
        ("Tratamiento de choque", "🧪", "danger", 20),
        ("Diagnóstico técnico", "🔎", "info", 30),
        ("Reparación", "🔧", "primary", 40),
        ("Cambio de arena", "🏖", "secondary", 50),
        ("Instalación", "⚙️", "primary", 60),
        ("Revisión de equipos", "🛠", "info", 70),
        ("Limpieza profunda", "🧹", "success", 80),
        ("Otro", "📌", "secondary", 99),
    ]
    for nombre, icono, color, orden in datos:
        Tipo.objects.get_or_create(nombre=nombre, defaults={"icono": icono, "color": color, "orden": orden, "activo": True})


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("clientes", "0002_cliente_datos_app"),
        ("contratos", "0008_alter_contrato_cobro_mes_desfase_and_more"),
        ("trabajadores", "0004_pago_fin_periodo_servicio"),
    ]
    operations = [
        migrations.CreateModel(
            name="TipoOrdenTrabajo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, unique=True)),
                ("icono", models.CharField(blank=True, default="🛠", max_length=20)),
                ("color", models.CharField(blank=True, default="primary", max_length=20)),
                ("activo", models.BooleanField(default=True)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"verbose_name": "Tipo de orden de trabajo", "verbose_name_plural": "Tipos de órdenes de trabajo", "ordering": ["orden", "nombre"]},
        ),
        migrations.CreateModel(
            name="OrdenTrabajo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origen", models.CharField(choices=[("contrato", "Cliente con contrato"), ("puntual", "Cliente / visita puntual")], default="puntual", max_length=20)),
                ("nombre_contacto", models.CharField(max_length=150)),
                ("telefono", models.CharField(blank=True, default="", max_length=50)),
                ("ciudad", models.CharField(blank=True, default="", max_length=100)),
                ("sector_urbanizacion", models.CharField(blank=True, default="", max_length=150)),
                ("direccion", models.TextField(blank=True, default="")),
                ("enlace_google_maps", models.URLField(blank=True, default="", max_length=500)),
                ("fecha", models.DateField(db_index=True)),
                ("hora", models.TimeField(blank=True, null=True)),
                ("estado", models.CharField(choices=[("pendiente", "Pendiente"), ("en_proceso", "En proceso"), ("completada", "Completada"), ("cancelada", "Cancelada")], db_index=True, default="pendiente", max_length=20)),
                ("titulo", models.CharField(blank=True, default="", max_length=160)),
                ("observaciones_admin", models.TextField(blank=True, default="")),
                ("reporte_trabajador", models.TextField(blank=True, default="")),
                ("valor_cliente", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("pago_trabajador", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("cortesia", models.BooleanField(default=False, help_text="Orden sin cobro adicional al cliente.")),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
                ("iniciada_en", models.DateTimeField(blank=True, null=True)),
                ("completada_en", models.DateTimeField(blank=True, null=True)),
                ("cliente", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordenes_trabajo", to="clientes.cliente")),
                ("contrato", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordenes_trabajo", to="contratos.contrato")),
                ("creada_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="ordenes_trabajo_creadas", to=settings.AUTH_USER_MODEL)),
                ("tipo", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordenes", to="ordenes_trabajo.tipoordentrabajo")),
                ("trabajador", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ordenes_trabajo", to="trabajadores.trabajador")),
            ],
            options={"verbose_name": "Orden de trabajo", "verbose_name_plural": "Órdenes de trabajo", "ordering": ["fecha", "hora", "id"]},
        ),
        migrations.CreateModel(
            name="FotoOrdenTrabajo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("imagen", models.ImageField(upload_to="ordenes_trabajo/")),
                ("tipo", models.CharField(choices=[("antes", "Antes"), ("durante", "Durante"), ("despues", "Después"), ("otro", "Otro")], default="otro", max_length=20)),
                ("descripcion", models.CharField(blank=True, default="", max_length=180)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("orden", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="fotos", to="ordenes_trabajo.ordentrabajo")),
            ],
            options={"ordering": ["creada_en", "id"]},
        ),
        migrations.AddIndex(model_name="ordentrabajo", index=models.Index(fields=["fecha", "estado"], name="ordenes_tra_fecha_2fd66d_idx")),
        migrations.AddIndex(model_name="ordentrabajo", index=models.Index(fields=["trabajador", "fecha"], name="ordenes_tra_trabaja_4095c7_idx")),
        migrations.RunPython(crear_tipos, migrations.RunPython.noop),
    ]
