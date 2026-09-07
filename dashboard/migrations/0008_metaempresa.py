from datetime import date
from django.db import migrations, models


def crear_metas_iniciales(apps, schema_editor):
    MetaEmpresa = apps.get_model("dashboard", "MetaEmpresa")
    metas = [
        {
            "nombre": "Cerrar 2026 con 60 contratos activos",
            "objetivo": 60,
            "fecha_inicio": date(2026, 9, 7),
            "fecha_fin": date(2026, 12, 31),
            "orden": 1,
        },
        {
            "nombre": "Cerrar 2027 con 150 contratos activos",
            "objetivo": 150,
            "fecha_inicio": date(2027, 1, 1),
            "fecha_fin": date(2027, 12, 31),
            "orden": 2,
        },
        {
            "nombre": "Cerrar 2028 con 350 contratos activos",
            "objetivo": 350,
            "fecha_inicio": date(2028, 1, 1),
            "fecha_fin": date(2028, 12, 31),
            "orden": 3,
        },
    ]
    for meta in metas:
        MetaEmpresa.objects.get_or_create(
            nombre=meta["nombre"],
            defaults={
                "metrica": "contratos_activos",
                "objetivo": meta["objetivo"],
                "fecha_inicio": meta["fecha_inicio"],
                "fecha_fin": meta["fecha_fin"],
                "estado": "activa",
                "orden": meta["orden"],
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0006_notificacion_referencia_id_notificacion_tipo_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="MetaEmpresa",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=140)),
                ("metrica", models.CharField(choices=[("contratos_activos","Contratos activos")], db_index=True, default="contratos_activos", max_length=40)),
                ("objetivo", models.PositiveIntegerField()),
                ("fecha_inicio", models.DateField()),
                ("fecha_fin", models.DateField(db_index=True)),
                ("estado", models.CharField(choices=[("activa","Activa"),("cumplida","Cumplida"),("pausada","Pausada")], db_index=True, default="activa", max_length=12)),
                ("orden", models.PositiveSmallIntegerField(default=0)),
                ("creada_en", models.DateTimeField(auto_now_add=True)),
                ("actualizada_en", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Meta empresarial",
                "verbose_name_plural": "Metas empresariales",
                "ordering": ["orden","fecha_fin","id"],
            },
        ),
        migrations.RunPython(crear_metas_iniciales, migrations.RunPython.noop),
    ]
