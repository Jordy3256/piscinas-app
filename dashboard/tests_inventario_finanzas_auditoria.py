from datetime import date
from decimal import Decimal

from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from dashboard.views import _resumen_inventario_contratos_en_sitio
from finanzas.models import Factura
from finanzas.views import _fila_cobro_factura, _fila_cobro_proyectado
from inventario.models import Insumo, InventarioContrato


class AuditoriaInventarioFinanzasTests(TestCase):
    def _cliente(self, nombre):
        return Cliente.objects.create(
            nombre=nombre,
            telefono="0999999999",
            ciudad="Guayaquil",
            direccion="Prueba",
        )

    def _contrato(self, cliente, **extra):
        defaults = dict(
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("100.00"),
            valor_tecnico_mensual=Decimal("0.00"),
            fecha_inicio=date(2026, 9, 1),
            activo=True,
            quimicos_proveedor="jvaqua",
            quimicos_almacenamiento="contrato",
        )
        defaults.update(extra)
        return Contrato.objects.create(cliente=cliente, **defaults)

    def test_inventario_por_contrato_incluye_contratos_sin_productos(self):
        c1 = self._contrato(self._cliente("Contrato con inventario"))
        c2 = self._contrato(self._cliente("Contrato todavía sin productos"))

        insumo = Insumo.objects.create(
            nombre="Cloro prueba",
            codigo="TEST-CL",
            stock=Decimal("20.000"),
            costo=Decimal("2.5000"),
        )
        InventarioContrato.objects.create(
            contrato=c1,
            insumo=insumo,
            stock=Decimal("3.000"),
        )

        resumen = _resumen_inventario_contratos_en_sitio()
        por_id = {x["contrato"].pk: x for x in resumen}

        self.assertEqual(len(resumen), 2)
        self.assertTrue(por_id[c1.pk]["configurado"])
        self.assertEqual(len(por_id[c1.pk]["stocks"]), 1)
        self.assertFalse(por_id[c2.pk]["configurado"])
        self.assertEqual(len(por_id[c2.pk]["stocks"]), 0)


    def test_factura_existente_mantiene_neto_iva_total(self):
        contrato = self._contrato(
            self._cliente("Cliente factura IVA"),
            aplica_iva=True,
            precio_mensual=Decimal("100.00"),
        )
        factura = Factura.objects.create(
            cliente=contrato.cliente,
            contrato=contrato,
            periodo_anio=2026,
            periodo_mes=9,
            periodo_inicio=date(2026, 9, 1),
            periodo_fin=date(2026, 9, 30),
            fecha_vencimiento=date(2026, 9, 10),
            subtotal=Decimal("100.00"),
            impuesto=Decimal("15.00"),
            total=Decimal("115.00"),
            valor_contractual=Decimal("100.00"),
        )

        fila = _fila_cobro_factura(factura)

        self.assertEqual(fila["neto"], Decimal("100.00"))
        self.assertEqual(fila["iva"], Decimal("15.00"))
        self.assertEqual(fila["valor"], Decimal("115.00"))
        self.assertEqual(fila["neto"] + fila["iva"], fila["valor"])

    def test_proyeccion_financiera_suma_neto_mas_iva(self):
        contrato = self._contrato(
            self._cliente("Cliente IVA"),
            aplica_iva=True,
            precio_mensual=Decimal("100.00"),
        )
        cuota = {
            "fecha_vencimiento": date(2026, 9, 10),
            "cuota_numero": 1,
            "total_cuotas": 1,
            "valor": Decimal("100.00"),
        }
        promo = {"total": Decimal("100.00"), "promocion": None}

        fila = _fila_cobro_proyectado(contrato, cuota, promo)

        self.assertEqual(fila["neto"], Decimal("100.00"))
        self.assertEqual(fila["iva"], Decimal("15.00"))
        self.assertEqual(fila["valor"], Decimal("115.00"))
        self.assertEqual(fila["neto"] + fila["iva"], fila["valor"])
