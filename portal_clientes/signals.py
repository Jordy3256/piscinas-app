"""Genera aviso solo al registrar un pago nuevo; no reenvía pagos históricos."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from finanzas.models import PagoFactura
from .models import AvisoPortal

@receiver(post_save, sender=PagoFactura, dispatch_uid='portal_pago_factura_aviso')
def notificar_pago(sender, instance, created, **kwargs):
    if not created or not instance.activo: return
    factura=instance.factura
    if factura.estado == 'anulada': return
    if not factura.cliente_id or factura.contrato.cliente_id != factura.cliente_id: return
    AvisoPortal.objects.get_or_create(cliente_id=factura.cliente_id,clave=f'pago:{instance.pk}',defaults={
        'tipo':'pago','titulo':'Pago registrado',
        'detalle':f'Administración registró un pago de ${instance.monto:.2f} correspondiente a la factura {factura.numero}.',
    })
