from datetime import date
from django.db import migrations


def actualizar_metas(apps, schema_editor):
    MetaEmpresa = apps.get_model("dashboard", "MetaEmpresa")
    metas = [
        (2026, 60, 1),
        (2027, 150, 2),
        (2028, 300, 3),
        (2029, 500, 4),
        (2030, 750, 5),
        (2031, 1000, 6),
    ]
    for anio, objetivo, orden in metas:
        fecha_fin = date(anio, 12, 31)
        fecha_inicio = date(2026, 9, 7) if anio == 2026 else date(anio, 1, 1)
        existentes = MetaEmpresa.objects.filter(
            metrica="contratos_activos", fecha_fin=fecha_fin
        ).order_by("id")
        meta = existentes.first()
        if meta is None:
            meta = MetaEmpresa(
                metrica="contratos_activos",
                fecha_fin=fecha_fin,
            )
        meta.nombre = f"Cerrar {anio} con {objetivo} contratos activos"
        meta.objetivo = objetivo
        meta.fecha_inicio = fecha_inicio
        meta.estado = "activa"
        meta.orden = orden
        meta.save()


def revertir_metas(apps, schema_editor):
    # No se revierte automáticamente para no borrar metas empresariales ni datos
    # que hayan podido ser editados después de aplicar esta migración.
    pass


class Migration(migrations.Migration):
    dependencies = [("dashboard", "0008_metaempresa")]
    operations = [migrations.RunPython(actualizar_metas, revertir_metas)]
