"""Pruebas de regresión de la programación operativa de JVAQUA.

No alteran los registros reales: Django utiliza su base de pruebas aislada.
"""
from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase

from clientes.models import Cliente
from contratos.models import Contrato
from contratos.programacion import (
    cancelar_programacion_futura,
    generar_mantenimientos_contrato,
)
from mantenimientos.models import Mantenimiento
from trabajadores.models import Trabajador


class IntegridadProgramacionMantenimientosTests(TestCase):
    def setUp(self):
        self.cliente = Cliente.objects.create(nombre="Cliente auditoría", telefono="0999999999")
        usuario = User.objects.create_user(username="tecnico_auditoria")
        self.trabajador = Trabajador.objects.create(user=usuario, telefono="0999999999")
        self.contrato = Contrato.objects.create(
            cliente=self.cliente,
            tipo="semanal",
            frecuencia="1_semanal",
            forma_pago="adelantado",
            programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"),
            fecha_inicio=date(2027, 1, 1),
            tecnico_designado=self.trabajador,
            dias_visita=[0],
            generacion_automatica=True,
            activo=True,
            vigencia_meses=12,
        )
        self.desde = date(2027, 1, 4)
        self.hasta = date(2027, 1, 25)

    def _generar(self, **kwargs):
        return generar_mantenimientos_contrato(
            self.contrato, desde=self.desde, hasta=self.hasta, **kwargs
        )

    def test_regenerar_no_duplica_visitas_y_asigna_tecnico(self):
        primera = self._generar()
        segunda = self._generar()
        visitas = list(Mantenimiento.objects.filter(contrato=self.contrato).order_by("fecha"))
        self.assertEqual(primera["creados"], 4)
        self.assertEqual(segunda["creados"], 0)
        self.assertEqual(len(visitas), 4)
        self.assertEqual(len({visita.fecha for visita in visitas}), 4)
        for visita in visitas:
            self.assertTrue(visita.automatico)
            self.assertEqual(visita.estado, "pendiente")
            self.assertEqual(list(visita.trabajadores.values_list("pk", flat=True)), [self.trabajador.pk])

    def test_reconciliar_conserva_realizados_y_visitas_manuales(self):
        self._generar()
        realizado = Mantenimiento.objects.get(contrato=self.contrato, fecha=self.desde)
        realizado.estado = "realizado"
        realizado.save(update_fields=["estado"])
        manual = Mantenimiento.objects.create(
            cliente=self.cliente, contrato=self.contrato,
            fecha=date(2027, 1, 6), estado="pendiente", automatico=False,
        )
        self._generar(reconciliar=True)
        realizado.refresh_from_db()
        manual.refresh_from_db()
        self.assertEqual(realizado.estado, "realizado")
        self.assertFalse(manual.automatico)
        self.assertEqual(Mantenimiento.objects.filter(contrato=self.contrato, fecha=self.desde).count(), 1)
        self.assertEqual(Mantenimiento.objects.filter(contrato=self.contrato).count(), 5)

    def test_cancelar_programacion_solo_elimina_automaticos_pendientes(self):
        self._generar()
        realizado = Mantenimiento.objects.get(contrato=self.contrato, fecha=self.desde)
        realizado.estado = "realizado"
        realizado.save(update_fields=["estado"])
        manual = Mantenimiento.objects.create(
            cliente=self.cliente, contrato=self.contrato,
            fecha=date(2027, 1, 6), estado="pendiente", automatico=False,
        )
        cancelar_programacion_futura(self.contrato, desde=self.desde)
        self.assertTrue(Mantenimiento.objects.filter(pk=realizado.pk).exists())
        self.assertTrue(Mantenimiento.objects.filter(pk=manual.pk).exists())
        self.assertEqual(Mantenimiento.objects.filter(contrato=self.contrato).count(), 2)
        self.contrato.refresh_from_db()
        self.assertIsNone(self.contrato.programado_hasta)

    def test_contrato_inactivo_no_genera_visitas(self):
        self.contrato.activo = False
        self.contrato.save(update_fields=["activo"])
        resultado = self._generar()
        self.assertEqual(resultado["creados"], 0)
        self.assertFalse(Mantenimiento.objects.filter(contrato=self.contrato).exists())


class SeguridadFotosMantenimientoTests(TestCase):
    """Una evidencia no debe ser visible a trabajadores ajenos a la visita."""

    def setUp(self):
        from django.urls import reverse
        from mantenimientos.models import FotoMantenimiento

        cliente = Cliente.objects.create(nombre="Cliente evidencia", telefono="0999999999")
        tecnico_user = User.objects.create_user(username="tecnico_foto_autorizado")
        ajeno_user = User.objects.create_user(username="tecnico_foto_ajeno")
        from django.contrib.auth.models import Group
        grupo_trabajadores, _ = Group.objects.get_or_create(name="Trabajadores")
        tecnico_user.groups.add(grupo_trabajadores)
        ajeno_user.groups.add(grupo_trabajadores)
        self.tecnico = Trabajador.objects.create(user=tecnico_user, telefono="0999999999")
        self.ajeno = Trabajador.objects.create(user=ajeno_user, telefono="0999999998")
        contrato = Contrato.objects.create(
            cliente=cliente, tipo="semanal", frecuencia="1_semanal",
            forma_pago="adelantado", programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"), fecha_inicio=date(2027, 1, 1),
            tecnico_designado=self.tecnico, activo=True,
        )
        visita = Mantenimiento.objects.create(
            cliente=cliente, contrato=contrato, fecha=date(2027, 1, 4)
        )
        visita.trabajadores.add(self.tecnico)
        foto = FotoMantenimiento.objects.create(
            mantenimiento=visita, imagen="mantenimientos/evidencia_inexistente.jpg"
        )
        self.url = reverse("foto_mantenimiento_archivo", args=[foto.pk])
        self.tecnico_user = tecnico_user
        self.ajeno_user = ajeno_user
        self.admin_user = User.objects.create_superuser(
            username="admin_foto_auditoria", email="admin@example.test", password="test-password"
        )

    def test_trabajador_no_asignado_no_puede_abrir_foto(self):
        self.client.force_login(self.ajeno_user)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 403)

    def test_trabajador_asignado_puede_consultar_foto(self):
        self.client.force_login(self.tecnico_user)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)

    def test_administracion_puede_consultar_foto(self):
        self.client.force_login(self.admin_user)
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)


class CierreMantenimientoFotosObligatoriasTests(TestCase):
    """Solo las tres fotos son obligatorias; el técnico no puede reabrir ni editar."""

    def setUp(self):
        from django.contrib.auth.models import Group
        self.cliente = Cliente.objects.create(nombre="Cliente cierre", telefono="0999999999")
        self.usuario = User.objects.create_user(username="tecnico_cierre")
        grupo, _ = Group.objects.get_or_create(name="Trabajadores")
        self.usuario.groups.add(grupo)
        self.tecnico = Trabajador.objects.create(user=self.usuario, telefono="0999999999")
        self.contrato = Contrato.objects.create(
            cliente=self.cliente, tipo="semanal", frecuencia="1_semanal",
            forma_pago="adelantado", programacion_cobro="inicio_periodo",
            precio_mensual=Decimal("55.00"), fecha_inicio=date(2027, 1, 1),
            tecnico_designado=self.tecnico, activo=True,
        )
        self.visita = Mantenimiento.objects.create(
            cliente=self.cliente, contrato=self.contrato, fecha=date(2027, 1, 4)
        )
        self.visita.trabajadores.add(self.tecnico)
        self.url = f"/dashboard/mantenimientos/{self.visita.pk}/"
        self.client.force_login(self.usuario)

    def _agregar_fotos(self, nombres):
        from mantenimientos.models import FotoMantenimiento
        for indice, nombre in enumerate(nombres):
            FotoMantenimiento.objects.create(
                mantenimiento=self.visita,
                descripcion=nombre,
                imagen=f"mantenimientos/prueba_cierre_{indice}.jpg",
            )

    def test_sin_fotografias_no_puede_finalizar(self):
        respuesta = self.client.post(self.url, {"accion": "finalizar_unificado"})
        self.assertEqual(respuesta.status_code, 302)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "pendiente")
        self.assertIsNone(self.visita.realizado_en)

    def test_con_una_foto_faltante_no_puede_finalizar(self):
        self._agregar_fotos(["Inicio de Mantenimiento", "Fin de Mantenimiento"])
        self.client.post(self.url, {"accion": "finalizar_unificado"})
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "pendiente")

    def test_tres_fotos_permiten_finalizar_sin_checklist(self):
        from mantenimientos.models import ChecklistMantenimiento
        self._agregar_fotos([
            "Inicio de Mantenimiento", "Fin de Mantenimiento", "Nivel PH y Cl"
        ])
        respuesta = self.client.post(self.url, {"accion": "finalizar_unificado"})
        self.assertEqual(respuesta.status_code, 302)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "realizado")
        self.assertIsNotNone(self.visita.realizado_en)
        checklist = ChecklistMantenimiento.objects.get(mantenimiento=self.visita)
        self.assertFalse(checklist.aspirado)
        self.assertFalse(checklist.cepillado)
        self.assertFalse(checklist.recoleccion_basura)

    def test_trabajador_no_reabre_ni_modifica_realizado(self):
        self.visita.estado = "realizado"
        self.visita.observaciones = "Original"
        self.visita.save(update_fields=["estado", "observaciones"])
        for accion in ("marcar_pendiente", "guardar_borrador_unificado", "finalizar_unificado"):
            respuesta = self.client.post(self.url, {
                "accion": accion, "observaciones": "Manipulado",
            })
            self.assertEqual(respuesta.status_code, 302)
            self.visita.refresh_from_db()
            self.assertEqual(self.visita.estado, "realizado")
            self.assertEqual(self.visita.observaciones, "Original")

    def test_administracion_puede_reabrir_realizado(self):
        admin = User.objects.create_superuser(
            username="admin_cierre", email="admin-cierre@example.test", password="prueba"
        )
        self.visita.estado = "realizado"
        self.visita.save(update_fields=["estado"])
        self.client.force_login(admin)
        respuesta = self.client.post(self.url, {"accion": "marcar_pendiente"})
        self.assertEqual(respuesta.status_code, 302)
        self.visita.refresh_from_db()
        self.assertEqual(self.visita.estado, "pendiente")
