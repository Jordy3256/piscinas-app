"""Elimina los avisos redundantes de reporte ya almacenados."""
from django.db import migrations


def eliminar_avisos_reporte(apps, schema_editor):
    Aviso = apps.get_model('portal_clientes', 'NotificacionMantenimientoCliente')
    Aviso.objects.using(schema_editor.connection.alias).filter(tipo='reporte').delete()


class Migration(migrations.Migration):
    dependencies = [
        ('portal_clientes', '0004_notificaciones_mantenimiento'),
    ]
    operations = [
        migrations.RunPython(eliminar_avisos_reporte, migrations.RunPython.noop),
    ]
