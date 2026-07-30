from decimal import Decimal

from django import forms

from .models import Egreso, Ingreso


class DateInput(forms.DateInput):
    input_type = "date"


class BaseMovimientoForm(forms.ModelForm):
    def clean(self):
        cleaned = super().clean()
        total = cleaned.get("total") or Decimal("0.00")
        pagado = cleaned.get("monto_pagado") or Decimal("0.00")
        if pagado > total:
            self.add_error("monto_pagado", "El valor pagado no puede superar el total.")
        return cleaned


class IngresoForm(BaseMovimientoForm):
    class Meta:
        model = Ingreso
        fields = [
            "cliente", "contrato", "concepto", "total", "monto_pagado", "fecha",
            "fecha_vencimiento", "fecha_cobro", "metodo_pago", "ciudad",
            "comprobante", "observaciones",
        ]
        widgets = {
            "fecha": DateInput(),
            "fecha_vencimiento": DateInput(),
            "fecha_cobro": DateInput(),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "total": "Valor total",
            "monto_pagado": "Valor cobrado",
            "fecha": "Fecha de registro",
        }


class EgresoForm(BaseMovimientoForm):
    total = forms.DecimalField(required=False, disabled=True, label="Total calculado")

    class Meta:
        model = Egreso
        fields = [
            "concepto", "categoria", "cantidad", "costo_unitario", "total", "monto_pagado",
            "fecha", "fecha_vencimiento", "metodo_pago", "proveedor", "ciudad_proyecto",
            "aprobado", "comprobante", "observaciones",
        ]
        widgets = {
            "fecha": DateInput(),
            "fecha_vencimiento": DateInput(),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "costo_unitario": "Costo unitario",
            "monto_pagado": "Valor pagado",
            "ciudad_proyecto": "Ciudad o proyecto",
        }

    def clean(self):
        cleaned = forms.ModelForm.clean(self)
        cantidad = cleaned.get("cantidad") or 0
        costo = cleaned.get("costo_unitario") or Decimal("0.00")
        total = Decimal(cantidad) * costo
        pagado = cleaned.get("monto_pagado") or Decimal("0.00")
        if pagado > total:
            self.add_error("monto_pagado", "El valor pagado no puede superar el total calculado.")
        return cleaned
