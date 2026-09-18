from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from contratos.models import Contrato
from inventario.models import Insumo
from mantenimientos.models import Mantenimiento, UsoInsumo
from trabajadores.models import Trabajador


class WorkerFinancialPrivacyTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(
            nombre="Cliente privacidad",
            telefono="0991111111",
            ciudad="Quito",
            direccion="Dirección",
        )
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("100.00"),
            fecha_inicio=date(2026, 9, 1),
            generacion_automatica=False,
            quimicos_proveedor="cliente",
            activo=True,
        )
        self.user_worker = User.objects.create_user("worker-privacy", password="test12345")
        grupo, _ = Group.objects.get_or_create(name="Trabajadores")
        self.user_worker.groups.add(grupo)
        self.trabajador = Trabajador.objects.create(
            user=self.user_worker,
            telefono="0992222222",
            activo=True,
        )
        self.mantenimiento = Mantenimiento.objects.create(
            cliente=self.cliente,
            contrato=self.contrato,
            fecha=date(2026, 9, 17),
            estado="realizado",
            automatico=False,
        )
        self.mantenimiento.trabajadores.add(self.trabajador)
        self.insumo = Insumo.objects.create(
            nombre="Cloro prueba",
            categoria="quimicos",
            unidad_base="kg",
            costo=Decimal("12.3400"),
            stock=Decimal("10.000"),
        )
        UsoInsumo.objects.create(
            mantenimiento=self.mantenimiento,
            insumo=self.insumo,
            trabajador=self.trabajador,
            cantidad=Decimal("1.000"),
            cantidad_ingresada=Decimal("1.000"),
            unidad_registro="kg",
            costo_unitario=Decimal("12.3400"),
            costo_total=Decimal("12.34"),
            origen_inventario="cliente",
        )

    def test_trabajador_ve_producto_y_cantidad_pero_no_costos(self):
        self.client.force_login(self.user_worker)
        response = self.client.get(reverse("mantenimiento_detalle", args=[self.mantenimiento.pk]))
        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode("utf-8")
        self.assertIn("Cloro prueba", contenido)
        self.assertNotIn("Costo químico actual", contenido)
        self.assertEqual(response.context["total_egresos"], Decimal("0.00"))

    def test_administrador_si_ve_costos(self):
        admin = User.objects.create_user("admin-privacy", password="test12345", is_staff=True)
        self.client.force_login(admin)
        response = self.client.get(reverse("mantenimiento_detalle", args=[self.mantenimiento.pk]))
        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode("utf-8")
        self.assertIn("Costo químico actual", contenido)
        self.assertEqual(response.context["total_egresos"], Decimal("12.34"))
