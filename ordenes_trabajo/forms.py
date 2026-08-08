from django import forms
from django.utils import timezone

from clientes.models import Cliente
from contratos.models import Contrato
from trabajadores.models import Trabajador
from .models import OrdenTrabajo, TipoOrdenTrabajo


class OrdenTrabajoForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo
        fields = [
            "origen", "tipo", "cliente", "contrato",
            "nombre_contacto", "telefono", "ciudad", "sector_urbanizacion", "direccion", "enlace_google_maps",
            "fecha", "hora", "trabajador", "titulo", "observaciones_admin",
            "cortesia", "valor_cliente", "pago_trabajador",
        ]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
            "direccion": forms.Textarea(attrs={"rows": 2}),
            "observaciones_admin": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, contrato_inicial=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].queryset = TipoOrdenTrabajo.objects.filter(activo=True)
        self.fields["trabajador"].queryset = Trabajador.objects.filter(activo=True).select_related("user").order_by("user__first_name", "user__username")
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=True).order_by("nombre")
        self.fields["contrato"].queryset = Contrato.objects.filter(activo=True).select_related("cliente").order_by("cliente__nombre", "id")
        for field in self.fields.values():
            css = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            field.widget.attrs["class"] = css

        if not self.instance.pk and not self.initial.get("fecha"):
            self.initial["fecha"] = timezone.localdate()
        if contrato_inicial is not None:
            c = contrato_inicial.cliente
            self.initial.update({
                "origen": "contrato",
                "contrato": contrato_inicial,
                "cliente": c,
                "nombre_contacto": c.nombre,
                "telefono": c.telefono,
                "ciudad": c.ciudad,
                "sector_urbanizacion": c.sector_urbanizacion,
                "direccion": c.direccion,
                "enlace_google_maps": c.enlace_google_maps,
                "trabajador": contrato_inicial.tecnico_designado,
            })

    def clean(self):
        cleaned = super().clean()
        origen = cleaned.get("origen")
        contrato = cleaned.get("contrato")
        if origen == "contrato" and not contrato:
            self.add_error("contrato", "Selecciona el contrato relacionado.")
        if origen == "puntual" and not (cleaned.get("nombre_contacto") or "").strip():
            self.add_error("nombre_contacto", "Indica el nombre de la persona o cliente.")
        if cleaned.get("cortesia"):
            cleaned["valor_cliente"] = None
        return cleaned
