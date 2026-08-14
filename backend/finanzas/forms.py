from decimal import Decimal
from datetime import date

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

from .models import Factura, PagoFactura, PagoTrabajador, MovimientoFinancieroMixin


class PagoFacturaForm(forms.ModelForm):
    class Meta:
        model = PagoFactura
        fields = ["monto", "fecha", "metodo_pago", "referencia", "comprobante", "observaciones"]
        widgets = {
            "fecha": DateInput(),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "monto": "Valor recibido",
            "fecha": "Fecha del pago",
            "metodo_pago": "Forma de pago",
            "referencia": "Número de referencia",
        }

    def __init__(self, *args, factura=None, **kwargs):
        self.factura = factura
        super().__init__(*args, **kwargs)
        if factura and not self.is_bound:
            self.fields["monto"].initial = factura.saldo

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if self.factura and monto > self.factura.saldo:
            raise forms.ValidationError(f"El pago no puede superar el saldo pendiente de ${self.factura.saldo:.2f}.")
        return monto


class FacturaFiltroForm(forms.Form):
    ESTADOS = [("", "Todos los estados")] + Factura.ESTADO_CHOICES
    q = forms.CharField(required=False)
    estado = forms.ChoiceField(required=False, choices=ESTADOS)
    anio = forms.IntegerField(required=False)
    mes = forms.IntegerField(required=False, min_value=1, max_value=12)


class PagoTrabajadorForm(forms.ModelForm):
    class Meta:
        model = PagoTrabajador
        fields = ["monto", "fecha", "metodo_pago", "referencia", "comprobante", "observaciones"]
        widgets = {"fecha": DateInput(), "observaciones": forms.Textarea(attrs={"rows": 3})}
        labels = {"monto": "Valor pagado", "fecha": "Fecha del pago", "metodo_pago": "Forma de pago"}

    def __init__(self, *args, obligacion=None, **kwargs):
        self.obligacion = obligacion
        super().__init__(*args, **kwargs)
        if obligacion and not self.is_bound:
            self.fields["monto"].initial = obligacion.saldo

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if self.obligacion and monto > self.obligacion.saldo:
            raise forms.ValidationError(f"El pago no puede superar el saldo pendiente de ${self.obligacion.saldo:.2f}.")
        return monto


class PagoConsolidadoTrabajadorForm(forms.Form):
    monto = forms.DecimalField(min_value=Decimal("0.01"), decimal_places=2, max_digits=12, label="Valor a pagar")
    fecha = forms.DateField(widget=DateInput(), initial=date.today, label="Fecha del pago")
    metodo_pago = forms.ChoiceField(choices=MovimientoFinancieroMixin.METODO_CHOICES, initial="transferencia", label="Forma de pago")
    referencia = forms.CharField(required=False, max_length=120, label="Número de referencia")
    comprobante = forms.FileField(required=False)
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, saldo_total=None, **kwargs):
        self.saldo_total = saldo_total or Decimal("0.00")
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.fields["monto"].initial = self.saldo_total

    def clean_monto(self):
        monto = self.cleaned_data["monto"]
        if monto > self.saldo_total:
            raise forms.ValidationError(f"El pago no puede superar el saldo total de ${self.saldo_total:.2f}.")
        return monto
