from django.db import migrations, models


def completar_periodos(apps, schema_editor):
    Obligacion = apps.get_model("finanzas", "ObligacionTrabajador")
    for obligacion in Obligacion.objects.select_related("contrato").all().iterator():
        contrato = obligacion.contrato
        try:
            inicio, fin = contrato.periodo_servicio(obligacion.periodo_anio, obligacion.periodo_mes)
        except Exception:
            # Compatibilidad con el modelo histórico dentro de migraciones.
            from calendar import monthrange
            from datetime import date
            dia = getattr(contrato, "periodo_dia_inicio", None) or contrato.fecha_inicio.day
            dia_inicio = min(dia, monthrange(obligacion.periodo_anio, obligacion.periodo_mes)[1])
            inicio = date(obligacion.periodo_anio, obligacion.periodo_mes, dia_inicio)
            if obligacion.periodo_mes == 12:
                anio_fin, mes_fin = obligacion.periodo_anio + 1, 1
            else:
                anio_fin, mes_fin = obligacion.periodo_anio, obligacion.periodo_mes + 1
            fin = date(anio_fin, mes_fin, min(dia, monthrange(anio_fin, mes_fin)[1]))
        obligacion.periodo_servicio_inicio = inicio
        obligacion.periodo_servicio_fin = fin
        obligacion.save(update_fields=["periodo_servicio_inicio", "periodo_servicio_fin"])


def limpiar_periodos(apps, schema_editor):
    Obligacion = apps.get_model("finanzas", "ObligacionTrabajador")
    Obligacion.objects.update(periodo_servicio_inicio=None, periodo_servicio_fin=None)


class Migration(migrations.Migration):
    dependencies = [("finanzas", "0012_anticipotrabajador")]
    operations = [
        migrations.AddField(
            model_name="obligaciontrabajador",
            name="periodo_servicio_inicio",
            field=models.DateField(blank=True, db_index=True, help_text="Fecha inicial del servicio que origina esta obligación. Se conserva históricamente.", null=True),
        ),
        migrations.AddField(
            model_name="obligaciontrabajador",
            name="periodo_servicio_fin",
            field=models.DateField(blank=True, db_index=True, help_text="Fecha final del servicio que origina esta obligación. Se conserva históricamente.", null=True),
        ),
        migrations.RunPython(completar_periodos, limpiar_periodos),
    ]
