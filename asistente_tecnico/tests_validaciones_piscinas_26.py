"""Regresión comercial AQUO360: validación de fichas, cuotas e independencia de datos."""
import unittest
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


    def test_rechaza_dimensiones_no_validas(self):
        for valor in ("Infinity", "NaN", "100000"):
            with self.subTest(largo=valor):
                self._post(largo_m=valor)
                self.assertEqual(PiscinaSuscriptor.objects.filter(suscriptor=self.perfil).count(), 0)
