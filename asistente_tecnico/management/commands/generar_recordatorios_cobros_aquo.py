from django.core.management.base import BaseCommand
from django.utils import timezone
from asistente_tecnico.cartera_digital import crear_cobros_mes, generar_avisos_cobros
from asistente_tecnico.models import PerfilSuscriptor


class Command(BaseCommand):
    help = "Genera cargos del mes y recordatorios internos de cobros AQUO360 Empresarial (ejecutar diariamente)"

    def handle(self, *args, **options):
        hoy = timezone.localdate()
        cargos = 0
        for perfil in PerfilSuscriptor.objects.filter(plan="empresarial", estado="activo"):
            if perfil.tiene_acceso:
                cargos += crear_cobros_mes(perfil, hoy.year, hoy.month)
        avisos = generar_avisos_cobros(hoy)
        self.stdout.write(self.style.SUCCESS(f"Cargos nuevos: {cargos}; avisos internos nuevos: {avisos}"))
