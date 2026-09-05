from django import forms
from django.utils.text import slugify
from .models import CategoriaAcademia, LeccionAcademia, ArticuloBiblioteca, ConsejoJVAQUA, ContenidoAcademia, ImagenContenidoAcademia, MaterialAudiovisualAcademia, ExperienciaConocimiento


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


class ContenidoAcademiaForm(StyledModelForm):
    class Meta:
        model = ContenidoAcademia
        fields = [
            "tipo", "codigo", "titulo", "resumen", "imagen_principal", "nivel", "tiempo_lectura_min",
            "estado", "version", "introduccion", "contenido", "procedimiento", "herramientas_materiales",
            "funcionamiento", "componentes", "mantenimiento", "fallas_frecuentes", "buenas_practicas",
            "errores_comunes", "recomendaciones_jvaqua", "referencias_tecnicas", "etiquetas", "acceso", "modulo_curso", "orden_curso", "relacionados", "orden",
        ]
        widgets = {
            "introduccion": forms.Textarea(attrs={"rows": 4}),
            "contenido": forms.Textarea(attrs={"rows": 9}),
            "procedimiento": forms.Textarea(attrs={"rows": 7}),
            "herramientas_materiales": forms.Textarea(attrs={"rows": 4}),
            "funcionamiento": forms.Textarea(attrs={"rows": 5}),
            "componentes": forms.Textarea(attrs={"rows": 4}),
            "mantenimiento": forms.Textarea(attrs={"rows": 5}),
            "fallas_frecuentes": forms.Textarea(attrs={"rows": 5}),
            "buenas_practicas": forms.Textarea(attrs={"rows": 5}),
            "errores_comunes": forms.Textarea(attrs={"rows": 5}),
            "recomendaciones_jvaqua": forms.Textarea(attrs={"rows": 5}),
            "referencias_tecnicas": forms.Textarea(attrs={"rows": 4}),
            "relacionados": forms.SelectMultiple(attrs={"size": 8}),
        }

    def save(self, commit=True):
        obj = super().save(commit=False)
        if not obj.slug:
            base = slugify(obj.titulo) or "contenido"
            slug = base
            n = 2
            while ContenidoAcademia.objects.exclude(pk=obj.pk).filter(slug=slug).exists():
                slug = f"{base}-{n}"
                n += 1
            obj.slug = slug
        if commit:
            obj.save()
            self.save_m2m()
        return obj


class ImagenContenidoAcademiaForm(StyledModelForm):
    class Meta:
        model = ImagenContenidoAcademia
        fields = ["imagen", "titulo", "descripcion", "orden"]


class MaterialAudiovisualAcademiaForm(StyledModelForm):
    class Meta:
        model = MaterialAudiovisualAcademia
        fields = ["tipo", "archivo", "titulo", "descripcion", "duracion_texto", "orden", "activo"]
        widgets = {
            "archivo": forms.ClearableFileInput(attrs={"accept": "video/*,audio/*"}),
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }

    def clean_archivo(self):
        archivo = self.cleaned_data.get("archivo")
        if not archivo:
            return archivo
        tipo = self.cleaned_data.get("tipo")
        content_type = getattr(archivo, "content_type", "") or ""
        if tipo == "video" and content_type and not content_type.startswith("video/"):
            raise forms.ValidationError("Selecciona un archivo de video válido.")
        if tipo == "audio" and content_type and not content_type.startswith("audio/"):
            raise forms.ValidationError("Selecciona un archivo de audio válido.")
        return archivo


class ExperienciaConocimientoForm(StyledModelForm):
    class Meta:
        model = ExperienciaConocimiento
        fields = ["titulo", "problema", "analisis", "solucion", "resultado", "aprendizaje", "estado", "destino_sugerido"]
        widgets = {k: forms.Textarea(attrs={"rows": 5}) for k in ["problema", "analisis", "solucion", "resultado", "aprendizaje"]}
