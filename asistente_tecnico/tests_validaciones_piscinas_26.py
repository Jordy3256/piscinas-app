"""Regresión comercial AQUO360: validación de fichas, cuotas e independencia de datos."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import PerfilSuscriptor, PiscinaSuscriptor


class ValidacionesPiscinasAquoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="aquo_qa_piscina", password="EjemploSeguro_123!")
        self.perfil = PerfilSuscriptor.objects.create(
            user=self.user, plan="individual", estado="activo",
            acceso_hasta=timezone.localdate() + timedelta(days=15),
        )
        self.client.force_login(self.user)
        self.url = reverse("asistente_tecnico:digital_piscina_nueva")

    def _post(self, **cambios):
        datos = {"nombre": "Piscina de prueba", "volumen_m3": "30"}
        datos.update(cambios)
        return self.client.post(self.url, datos)

    def test_rechaza_volumen_infinito_y_no_finito(self):
        for valor in ("Infinity", "-Infinity", "NaN", "10000000"):
            with self.subTest(volumen=valor):
                self.assertEqual(self._post(volumen_m3=valor).status_code, 200)
                self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 0)

    def test_rechaza_dimensiones_no_validas(self):
        for valor in ("Infinity", "NaN", "100000"):
            with self.subTest(largo=valor):
                self._post(largo_m=valor)
                self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 0)

    def test_limite_individual_impide_segunda_piscina(self):
        self.assertEqual(self._post().status_code, 302)
        self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 1)
        self._post(nombre="Segunda piscina")
        self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 1)

    def test_empresarial_permite_varias_piscinas_y_rechaza_importes_invalidos(self):
        self.perfil.plan = "empresarial"
        self.perfil.save(update_fields=["plan"])
        for valor in ("Infinity", "100000000", "12.999"):
            self._post(valor_mensual=valor)
            self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 0)
        for numero in range(4):
            self.assertEqual(self._post(nombre=f"Piscina {numero}", valor_mensual="95.00").status_code, 302)
        self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 4)

    def test_piscina_ajena_no_se_puede_editar(self):
        otro = get_user_model().objects.create_user(username="otro_aquo_qa", password="EjemploSeguro_123!")
        otro_perfil = PerfilSuscriptor.objects.create(user=otro, plan="individual", estado="activo",
            acceso_hasta=timezone.localdate() + timedelta(days=15))
        piscina = PiscinaSuscriptor.objects.create(suscriptor=otro_perfil, nombre="Privada", volumen_m3=Decimal("25"))
        url = reverse("asistente_tecnico:digital_piscina_editar", args=[piscina.pk])
        respuesta = self.client.post(url, {"nombre": "Alterado", "volumen_m3": "50"})
        self.assertEqual(respuesta.status_code, 404)
        piscina.refresh_from_db()
        self.assertEqual(piscina.nombre, "Privada")
