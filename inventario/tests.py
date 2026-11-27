"""Regresiones de permisos y existencias del inventario JVAQUA.

Se ejecutan en la base de datos temporal de pruebas de Django.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente
from contratos.models import Contrato
from inventario.models import Insumo, InventarioContrato, InventarioTrabajador, MovimientoInventario
from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador


class SeguridadYExistenciasInventarioTests(TestCase):
    def setUp(self):
        grupo, _ = Group.objects.get_or_create(name="Trabajadores")
        self.admin = User.objects.create_superuser("admin_inv_audit", "admin@example.test", "clave")
        self.usuario = User.objects.create_user("tecnico_inv_audit", password="clave")
        self.usuario.groups.add(grupo)
        self.trabajador = Trabajador.objects.create(user=self.usuario, telefono="0999999999")
        self.otro_usuario = User.objects.create_user("otro_inv_audit", password="clave")
        self.otro_usuario.groups.add(grupo)
        self.otro = Trabajador.objects.create(user=self.otro_usuario, telefono="0999999998")
        self.insumo = Insumo.objects.create(
            nombre="Producto auditoría privacidad", stock=Decimal("10.000"),
            stock_minimo=Decimal("1.000"), costo=Decimal("9876.5432"),
            precio=Decimal("8765.43"),
        )
        self.cliente = Cliente.objects.create(nombre="Cliente inventario auditoría", telefono="0999999999")
        self.contrato = Contrato.objects.create(
            cliente=self.cliente, tipo="semanal", frecuencia="1_semanal",
            forma_pago="adelantado", programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"), fecha_inicio=date(2027, 1, 1),
            tecnico_designado=self.otro, activo=True,
            quimicos_proveedor="jvaqua", quimicos_almacenamiento="contrato",
        )
        InventarioContrato.objects.create(contrato=self.contrato, insumo=self.insumo, stock=Decimal("3.000"))

    def _entregar(self, cantidad, usuario=None):
        self.client.force_login(usuario or self.admin)
        return self.client.post(reverse("inventario_entrega_trabajador"), {
            "trabajador_id": str(self.trabajador.pk), "insumo_id": str(self.insumo.pk),
            "cantidad": str(cantidad), "unidad": "base",
        })

    def _devolver(self, cantidad, usuario=None):
        self.client.force_login(usuario or self.admin)
        return self.client.post(reverse("inventario_devolucion_trabajador"), {
            "trabajador_id": str(self.trabajador.pk), "insumo_id": str(self.insumo.pk),
            "cantidad": str(cantidad), "unidad": "base",
        })

    def test_trabajador_no_puede_entregar_ni_devolver_productos(self):
        self.assertEqual(self._entregar("2", self.usuario).status_code, 403)
        self.assertEqual(self._devolver("1", self.usuario).status_code, 403)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock, Decimal("10.000"))
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_entrega_admin_actualiza_ambos_stocks_y_trazabilidad(self):
        self.assertEqual(self._entregar("2").status_code, 302)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock, Decimal("8.000"))
        self.assertEqual(InventarioTrabajador.objects.get(trabajador=self.trabajador, insumo=self.insumo).stock, Decimal("2.000"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="entrega", trabajador=self.trabajador).count(), 1)

    def test_entrega_sin_stock_no_produce_movimientos_parciales(self):
        self.assertEqual(self._entregar("11").status_code, 302)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock, Decimal("10.000"))
        self.assertFalse(InventarioTrabajador.objects.filter(trabajador=self.trabajador, insumo=self.insumo, stock__gt=0).exists())
        self.assertEqual(MovimientoInventario.objects.count(), 0)

    def test_devolucion_admin_restituye_stock_y_registra_movimiento(self):
        self._entregar("3")
        self.assertEqual(self._devolver("1").status_code, 302)
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock, Decimal("8.000"))
        self.assertEqual(InventarioTrabajador.objects.get(trabajador=self.trabajador, insumo=self.insumo).stock, Decimal("2.000"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="devolucion").count(), 1)

    def test_devolucion_excesiva_no_modifica_existencias(self):
        self._entregar("2")
        self._devolver("3")
        self.insumo.refresh_from_db()
        self.assertEqual(self.insumo.stock, Decimal("8.000"))
        self.assertEqual(InventarioTrabajador.objects.get(trabajador=self.trabajador, insumo=self.insumo).stock, Decimal("2.000"))
        self.assertEqual(MovimientoInventario.objects.filter(tipo="devolucion").count(), 0)

    def test_mi_inventario_no_expone_costos_ni_productos_ajenos(self):
        self._entregar("2")
        self.client.force_login(self.otro_usuario)
        respuesta = self.client.get(reverse("mi_inventario_trabajador"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "Producto auditoría privacidad")
        self.assertNotContains(respuesta, "9876.5432")
        self.assertNotContains(respuesta, "8765.43")
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse("mi_inventario_trabajador"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Producto auditoría privacidad")
        self.assertNotContains(respuesta, "9876.5432")
        self.assertNotContains(respuesta, "8765.43")

    def test_inventario_contrato_permite_responsable_actual_y_rechaza_ajeno(self):
        url = reverse("inventario_contrato_trabajador", args=[self.contrato.pk])
        self.client.force_login(self.otro_usuario)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_asignacion_historica_no_da_acceso_permanente_al_inventario(self):
        visita = Mantenimiento.objects.create(
            cliente=self.cliente, contrato=self.contrato, fecha=date(2026, 1, 4), estado="realizado"
        )
        visita.trabajadores.add(self.trabajador)
        self.client.force_login(self.usuario)
        url = reverse("inventario_contrato_trabajador", args=[self.contrato.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
