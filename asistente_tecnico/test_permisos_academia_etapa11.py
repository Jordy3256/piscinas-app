from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from .models import PerfilSuscriptor
from .views import _base_template


class PermisosAcademiaEtapa11Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("legacy-etapa11", password="x")
        PerfilSuscriptor.objects.create(user=self.user, estado="activo")
        self.client.force_login(self.user)

    def test_suscriptor_sin_rol_no_accede(self):
        for name, args, method in (
            ("inicio", (), self.client.get),
            ("academia_cms", (), self.client.get),
            ("academia_contenido_detalle", ("inexistente",), self.client.get),
            ("academia_contenido_completar", ("inexistente",), self.client.post),
            ("academia_contenido_favorito", ("inexistente",), self.client.post),
            ("academia_pdf_articulo", ("inexistente",), self.client.get),
            ("academia_pdf_categoria", ("inexistente",), self.client.get),
            ("academia_pdf_manual", (), self.client.get),
        ):
            with self.subTest(name=name):
                self.assertEqual(method(reverse("asistente_tecnico:" + name, args=args)).status_code, 403)

    def test_rol_trabajador_prevalece_sobre_perfil_historico(self):
        self.user.groups.add(Group.objects.get_or_create(name="Trabajadores")[0])
        self.assertEqual(_base_template(self.user), "dashboard/base_trabajador.html")
        self.assertEqual(self.client.get(reverse("asistente_tecnico:academia_cms")).status_code, 200)
