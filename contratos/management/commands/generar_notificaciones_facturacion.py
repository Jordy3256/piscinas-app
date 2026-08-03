from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from contratos.models import Contrato
from dashboard.models import Notificacion


class Command(BaseCommand):
    help = "Genera recordatorios internos para las facturas programadas de contratos activos."

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        administradores = get_user_model().objects.filter(is_active=True).filter(is_staff=True)
        creadas = 0
        contratos = Contrato.objects.filter(
            activo=True,
            requiere_factura=True,
            notificar_facturacion=True,
        ).select_related("cliente")
        for contrato in contratos:
            for desplazamiento in (0, 1):
                indice = hoy.year * 12 + hoy.month - 1 + desplazamiento
                anio, mes = indice // 12, indice % 12 + 1
                fecha_factura = contrato.fecha_programada_facturacion(anio, mes)
                if not fecha_factura:
                    continue
                fecha_aviso = fecha_factura - timedelta(days=contrato.notificacion_factura_dias_antes or 0)
                if fecha_aviso != hoy:
                    continue
                tipo = f"factura_{anio}{mes:02d}"
                for user in administradores:
                    _, creada = Notificacion.objects.get_or_create(
                        user=user,
                        tipo=tipo,
                        referencia_id=contrato.pk,
                        defaults={
                            "titulo": "Factura pendiente de emitir",
                            "mensaje": f"{contrato.cliente.nombre}: emitir factura del periodo {mes:02d}/{anio} el {fecha_factura:%d/%m/%Y}.",
                            "url": f"/dashboard/contratos/{contrato.pk}/",
                        },
                    )
                    creadas += int(creada)
        self.stdout.write(self.style.SUCCESS(f"Recordatorios creados: {creadas}"))
