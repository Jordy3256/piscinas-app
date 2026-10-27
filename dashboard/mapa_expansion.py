"""Mapa empresarial: lectura exclusivamente administrativa, sin geocodificación especulativa."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.db.models import Q
from contratos.models import Contrato


@login_required
@user_passes_test(lambda u: u.is_staff or u.is_superuser)
def mapa_expansion_view(request):
    modo = request.GET.get("modo", "activos")
    if modo not in ("activos", "historial", "todos"):
        modo = "activos"
    ciudad = (request.GET.get("ciudad") or "").strip()[:100]
    qs = Contrato.objects.select_related("cliente", "ciudad_ref", "tecnico_designado").order_by("id")
    # El estado del contrato es la fuente de verdad; nunca se eliminan los históricos.
    if modo == "activos":
        qs = qs.filter(activo=True)
    elif modo == "historial":
        qs = qs.filter(activo=False)
    ciudades = sorted({(c.ciudad or (str(c.ciudad_ref) if c.ciudad_ref_id else "")).strip() for c in Contrato.objects.all().only("ciudad", "ciudad_ref").select_related("ciudad_ref") if c.ciudad or c.ciudad_ref_id})
    if ciudad:
        qs = qs.filter(Q(ciudad__iexact=ciudad) | Q(ciudad_ref__nombre__iexact=ciudad))
    puntos = []
    pendientes = []
    for c in qs:
        lat, lon = c.latitud, c.longitud
        if lat is None or lon is None or not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
            pendientes.append({"id": c.pk, "cliente": str(c.cliente), "sector": c.sector_urbanizacion or "Sin sector"})
            continue
        puntos.append({
            "id": c.pk, "lat": float(lat), "lon": float(lon),
            "cliente": str(c.cliente), "ciudad": c.ciudad or (str(c.ciudad_ref) if c.ciudad_ref_id else ""),
            "sector": c.sector_urbanizacion or "", "direccion": c.direccion or "",
            "activo": c.activo, "frecuencia": c.get_frecuencia_display() if c.frecuencia else "",
            "tecnico_designado": str(c.tecnico_designado) if c.tecnico_designado_id else "Sin asignar",
        })
    return render(request, "dashboard/mapa_expansion.html", {
        "puntos": puntos, "pendientes": pendientes, "modo": modo,
        "ciudades": ciudades, "ciudad_seleccionada": ciudad,
        "total_activos": Contrato.objects.filter(activo=True).count(),
        "total_historicos": Contrato.objects.filter(activo=False).count(),
        "ciudades_activas": Contrato.objects.filter(activo=True).exclude(ciudad="").values("ciudad").distinct().count(),
    })
