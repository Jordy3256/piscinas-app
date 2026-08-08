from django import forms
from django.utils.text import slugify
from .models import CategoriaAcademia, LeccionAcademia, ArticuloBiblioteca, ConsejoJVAQUA


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            cls = "form-select" if isinstance(field.widget, forms.Select) else "form-control"
            if isinstance(field.widget, forms.CheckboxInput):
                cls = "form-check-input"
            field.widget.attrs.setdefault("class", cls)


class CategoriaAcademiaForm(StyledModelForm):
    class Meta:
        model = CategoriaAcademia
        fields = ["nombre", "descripcion", "icono", "orden", "activa"]

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.slug:
            base = slugify(obj.nombre) or "categoria"
            slug = base
            n = 2
            while CategoriaAcademia.objects.exclude(pk=obj.pk).filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            obj.slug = slug
        if commit:
            obj.save()
        return obj


class LeccionAcademiaForm(StyledModelForm):
    class Meta:
        model = LeccionAcademia
        fields = ["categoria", "titulo", "resumen", "contenido", "errores_evitar", "consejo_jvaqua", "duracion_minutos", "orden", "publicada"]
        widgets = {
            "contenido": forms.Textarea(attrs={"rows": 8}),
            "errores_evitar": forms.Textarea(attrs={"rows": 4}),
            "consejo_jvaqua": forms.Textarea(attrs={"rows": 4}),
        }


class ArticuloBibliotecaForm(StyledModelForm):
    class Meta:
        model = ArticuloBiblioteca
        fields = ["titulo", "categoria", "resumen", "funcionamiento", "componentes", "mantenimiento", "fallas_comunes", "recomendaciones", "palabras_clave", "orden", "publicada"]
        widgets = {k: forms.Textarea(attrs={"rows": 4}) for k in ["funcionamiento", "componentes", "mantenimiento", "fallas_comunes", "recomendaciones"]}


class ConsejoJVAQUAForm(StyledModelForm):
    class Meta:
        model = ConsejoJVAQUA
        fields = ["titulo", "texto", "categoria", "orden", "activo"]
        widgets = {"texto": forms.Textarea(attrs={"rows": 4})}
