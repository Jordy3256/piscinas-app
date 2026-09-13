from collections import defaultdict
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from contratos.models import Contrato
from finanzas.cuentas_por_cobrar import valores_promocion
from inventario.models import MovimientoInventario


D0 = Decimal("0.00")


def _q(value):
    return Decimal(value or 0).quantize(Decimal("0.01"))


def analizar_rentabilidad(*, hoy=None, ciudad=None):
    hoy = hoy or timezone.localdate()
    contratos_qs = (
        Contrato.objects.filter(activo=True, fecha_inicio__lte=hoy)
        .filter(Q(fecha_fin_contrato__isnull=True) | Q(fecha_fin_contrato__gte=hoy))
        .select_related("cliente", "tecnico_designado", "ciudad_ref", "cliente__ciudad_ref")
    )
    if ciudad is not None:
        contratos_qs = contratos_qs.filter(
            Q(ciudad_ref=ciudad) | Q(ciudad_ref__isnull=True, cliente__ciudad_ref=ciudad)
        )
    contratos = list(contratos_qs)

    # El sueldo fijo se distribuye GLOBALMENTE entre todos los contratos activos
    # del trabajador, incluso al analizar una sola ciudad.
    ids_fijos = {
        c.tecnico_designado_id for c in contratos
        if c.tecnico_designado and c.tecnico_designado.tipo_remuneracion == "mensual_fija"
    }
    contratos_globales_fijo = {
        tid: Contrato.objects.filter(activo=True, tecnico_designado_id=tid, fecha_inicio__lte=hoy)
        .filter(Q(fecha_fin_contrato__isnull=True) | Q(fecha_fin_contrato__gte=hoy)).count()
        for tid in ids_fijos
    }

    movimientos = (
        MovimientoInventario.objects.filter(
            tipo__in=["mantenimiento", "consumo_contrato"],
            fecha__year=hoy.year, fecha__month=hoy.month,
        ).select_related("mantenimiento")
    )
    quimicos = defaultdict(lambda: D0)
    for mov in movimientos:
        cid = mov.contrato_id or (mov.mantenimiento.contrato_id if mov.mantenimiento_id and mov.mantenimiento else None)
        if cid:
            quimicos[cid] += _q(mov.total_costo)

    filas=[]
    ciudades=defaultdict(lambda:{"ingreso":D0,"tecnico":D0,"quimicos":D0,"contratos":0})
    trabajadores=defaultdict(lambda:{"ingreso":D0,"costo":D0,"quimicos":D0,"contratos":0,"nombre":"Sin técnico"})
    total_ingreso=total_tecnico=total_quimicos=D0

    for c in contratos:
        promo = valores_promocion(c, hoy.year, hoy.month)
        ingreso = _q(promo["total"])  # base operativa, IVA excluido
        t=c.tecnico_designado
        if t and t.tipo_remuneracion == "mensual_fija":
            n=contratos_globales_fijo.get(t.pk,0)
            costo_tecnico=_q(Decimal(t.sueldo_mensual_fijo or 0)/Decimal(n)) if n else D0
        else:
            costo_tecnico=_q(c.valor_tecnico_mensual)
        costo_quimicos=_q(quimicos[c.pk])
        margen=_q(ingreso-costo_tecnico-costo_quimicos)
        pct=round(float((margen/ingreso)*100),1) if ingreso else 0.0
        quim_pct=round(float((costo_quimicos/ingreso)*100),1) if ingreso else 0.0
        if margen < 0:
            estado="perdida"
        elif pct < 15:
            estado="critico"
        elif pct < 25:
            estado="atencion"
        else:
            estado="saludable"
        ciudad_obj=c.ciudad_ref or c.cliente.ciudad_ref
        ciudad_nombre=ciudad_obj.nombre if ciudad_obj else (c.ciudad or c.cliente.ciudad or "Sin ciudad")
        fila={"contrato":c,"ingreso":ingreso,"tecnico":costo_tecnico,"quimicos":costo_quimicos,"margen":margen,"margen_pct":pct,"quimicos_pct":quim_pct,"estado":estado,"ciudad":ciudad_nombre,"promocion":promo.get("promocion")}
        filas.append(fila)
        total_ingreso+=ingreso; total_tecnico+=costo_tecnico; total_quimicos+=costo_quimicos
        cd=ciudades[ciudad_nombre]; cd["ingreso"]+=ingreso; cd["tecnico"]+=costo_tecnico; cd["quimicos"]+=costo_quimicos; cd["contratos"]+=1
        tid=t.pk if t else 0; td=trabajadores[tid]; td["nombre"]=str(t) if t else "Sin técnico"; td["ingreso"]+=ingreso; td["costo"]+=costo_tecnico; td["quimicos"]+=costo_quimicos; td["contratos"]+=1

    for f in filas:
        senales=[]
        if f["estado"] in {"perdida","critico"}: senales.append("Margen insuficiente")
        if f["quimicos_pct"] >= 20: senales.append("Costo químico elevado")
        if not f["contrato"].tecnico_designado_id: senales.append("Sin técnico")
        if f["promocion"]: senales.append("Promoción activa")
        f["senales"]=senales
    filas.sort(key=lambda x:(x["margen_pct"],x["margen"]))

    ranking_ciudades=[]
    for nombre,d in ciudades.items():
        margen=_q(d["ingreso"]-d["tecnico"]-d["quimicos"]); pct=round(float(margen/d["ingreso"]*100),1) if d["ingreso"] else 0
        ranking_ciudades.append({"nombre":nombre,**d,"margen":margen,"margen_pct":pct})
    ranking_ciudades.sort(key=lambda x:x["margen"],reverse=True)
    ranking_trabajadores=[]
    for _,d in trabajadores.items():
        margen=_q(d["ingreso"]-d["costo"]-d["quimicos"]); pct=round(float(margen/d["ingreso"]*100),1) if d["ingreso"] else 0
        ranking_trabajadores.append({**d,"margen":margen,"margen_pct":pct})
    ranking_trabajadores.sort(key=lambda x:x["margen"],reverse=True)

    margen_total=_q(total_ingreso-total_tecnico-total_quimicos)
    pct_total=round(float(margen_total/total_ingreso*100),1) if total_ingreso else 0
    return {
        "filas":filas,"ranking_ciudades":ranking_ciudades,"ranking_trabajadores":ranking_trabajadores,
        "ingreso":_q(total_ingreso),"tecnico":_q(total_tecnico),"quimicos":_q(total_quimicos),
        "margen":margen_total,"margen_pct":pct_total,"contratos":len(filas),
        "en_perdida":sum(1 for f in filas if f["estado"]=="perdida"),
        "criticos":sum(1 for f in filas if f["estado"]=="critico"),
        "atencion":sum(1 for f in filas if f["estado"]=="atencion"),
        "saludables":sum(1 for f in filas if f["estado"]=="saludable"),
    }
