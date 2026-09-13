from datetime import date
from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from clientes.models import Cliente
from contratos.models import Contrato
from dashboard.inteligencia_rentabilidad import analizar_rentabilidad
from trabajadores.models import Trabajador

class InteligenciaRentabilidadTests(TestCase):
    def test_sueldo_fijo_se_distribuye_entre_contratos(self):
        u=User.objects.create_user(username="tec_ri")
        t=Trabajador.objects.create(user=u, telefono="0990000000", tipo_remuneracion="mensual_fija", sueldo_mensual_fijo=Decimal("100.00"))
        for n in range(2):
            cli=Cliente.objects.create(nombre=f"Cliente {n}", telefono=f"099000000{n+1}", direccion="Test")
            Contrato.objects.create(cliente=cli, tipo="semanal", frecuencia="1_semanal", forma_pago="adelantado", programacion_cobro="inicio_periodo", precio_mensual=Decimal("100.00"), fecha_inicio=date(2026,9,1), tecnico_designado=t, dias_visita=[1], activo=True)
        data=analizar_rentabilidad(hoy=date(2026,9,12))
        self.assertEqual(data["tecnico"], Decimal("100.00"))
        self.assertEqual(data["ingreso"], Decimal("200.00"))
