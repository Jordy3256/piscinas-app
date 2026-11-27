from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from dashboard.models import Notificacion
from finanzas.alertas_financieras import _crear_para_admins


class RendimientoFase2Tests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(username="perf_admin", is_staff=True)
        self.otro = get_user_model().objects.create_user(username="perf_otro", is_staff=True)

    def test_contador_admin_no_sincroniza_finanzas_y_aisla_usuario(self):
        Notificacion.objects.create(user=self.admin, titulo="Pendiente", mensaje="Prueba")
        Notificacion.objects.create(user=self.admin, titulo="Leida", mensaje="Prueba", leida=True)
        Notificacion.objects.create(user=self.otro, titulo="Ajena", mensaje="Prueba")
        self.client.force_login(self.admin)
        with patch("finanzas.alertas_financieras.generar_alertas_financieras") as generar:
            respuesta = self.client.get(reverse("unread_count"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json(), {"count": 1})
        generar.assert_not_called()

    def test_alerta_identica_no_escribe_y_conserva_lectura(self):
        datos = dict(usuarios=[self.admin], tipo="cobro_hoy", referencia_id=123,
                     titulo="Cobro", mensaje="Pendiente", url="/dashboard/")
        _crear_para_admins(**datos)
        aviso = Notificacion.objects.get(user=self.admin, tipo="cobro_hoy")
        aviso.leida = True
        aviso.save(update_fields=["leida"])
        with self.assertNumQueries(1):
            _crear_para_admins(**datos)
        datos["mensaje"] = "Actualizado"
        _crear_para_admins(**datos)
        aviso.refresh_from_db()
        self.assertTrue(aviso.leida)
        self.assertEqual(aviso.mensaje, "Actualizado")
