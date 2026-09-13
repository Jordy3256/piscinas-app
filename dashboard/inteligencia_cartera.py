from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from finanzas.models import Factura

D0=Decimal("0.00")
def _money(v): return Decimal(v or 0).quantize(Decimal("0.01"))
def _city_q(c):
    return Q() if c is None else Q(contrato__ciudad_ref=c)|Q(contrato__ciudad_ref__isnull=True,cliente__ciudad_ref=c)
def _bucket(d):
    return "al_dia" if d<=0 else "1_15" if d<=15 else "16_30" if d<=30 else "31_60" if d<=60 else "61_mas"

def analizar_cartera_inteligente(*,hoy=None,ciudad=None):
    hoy=hoy or timezone.localdate()
    qs=(Factura.objects.exclude(estado__in=[Factura.ESTADO_ANULADA,Factura.ESTADO_PROMOCION])
        .filter(_city_q(ciudad)).select_related("cliente","contrato","contrato__ciudad_ref","cliente__ciudad_ref").prefetch_related("pagos"))
    buckets={k:{"label":l,"saldo":D0,"facturas":0} for k,l in [("al_dia","Por vencer / al día"),("1_15","1–15 días"),("16_30","16–30 días"),("31_60","31–60 días"),("61_mas","61+ días")]}
    clientes=defaultdict(lambda:{"cliente":None,"saldo":D0,"vencido":D0,"facturas":0,"vencidas":0,"max_dias":0,"reincidencia":0,"pagos_tardios":0,"proximo_vencimiento":None})
    pendientes=[]
    for f in qs:
        saldo=_money(f.saldo)
        if saldo<=0: continue
        dias=(hoy-f.fecha_vencimiento).days; key=_bucket(dias); vencida=dias>0
        buckets[key]["saldo"]+=saldo; buckets[key]["facturas"]+=1
        pendientes.append({"factura":f,"saldo":saldo,"dias":max(0,dias),"vencida":vencida,"bucket":key})
        c=clientes[f.cliente_id]; c["cliente"]=f.cliente; c["saldo"]+=saldo; c["facturas"]+=1
        if vencida:
            c["vencido"]+=saldo; c["vencidas"]+=1; c["max_dias"]=max(c["max_dias"],dias)
        elif c["proximo_vencimiento"] is None or f.fecha_vencimiento<c["proximo_vencimiento"]: c["proximo_vencimiento"]=f.fecha_vencimiento
    for f in qs.filter(fecha_vencimiento__gte=hoy-timedelta(days=365),fecha_vencimiento__lte=hoy):
        c=clientes.get(f.cliente_id)
        if not c: continue
        tardia=bool(f.pagada_en and f.pagada_en>f.fecha_vencimiento); vencida=f.saldo>0 and f.fecha_vencimiento<hoy
        if tardia or vencida: c["reincidencia"]+=1
        if tardia: c["pagos_tardios"]+=1
    ranking=[]
    for c in clientes.values():
        antig=min(40,int(c["max_dias"]/60*40)) if c["max_dias"] else 0
        monto=min(30,int(c["vencido"]/Decimal("500")*30)) if c["vencido"] else 0
        score=min(100,antig+monto+min(20,c["reincidencia"]*5)+min(10,c["vencidas"]*3))
        if c["vencido"]<=0: nivel,prioridad="al_dia","Por vencer"
        elif score>=70: nivel,prioridad="critica","Cobrar hoy"
        elif score>=40: nivel,prioridad="alta","Prioridad alta"
        else: nivel,prioridad="media","Seguimiento"
        ranking.append({**c,"score":score,"nivel":nivel,"prioridad":prioridad,"url_cliente":reverse("cliente_detalle",args=[c["cliente"].pk])})
    ranking.sort(key=lambda x:(x["score"],x["vencido"],x["max_dias"]),reverse=True)
    total=sum((x["saldo"] for x in pendientes),D0); vencido=sum((x["saldo"] for x in pendientes if x["vencida"]),D0)
    recuperable=sum((x["saldo"] for x in pendientes if x["vencida"] and x["dias"]<=30),D0)
    severo=buckets["31_60"]["saldo"]+buckets["61_mas"]["saldo"]
    proy=sum((x["saldo"] for x in pendientes if not x["vencida"] and x["factura"].fecha_vencimiento<=hoy+timedelta(days=30)),D0)
    senales=[]
    if buckets["61_mas"]["saldo"]>0: senales.append({"nivel":"critica","titulo":"Deuda con más de 60 días","texto":f"${buckets['61_mas']['saldo']:,.2f} requiere gestión prioritaria."})
    if ranking and ranking[0]["score"]>=70: senales.append({"nivel":"critica","titulo":"Clientes de cobro prioritario","texto":"Hay clientes con combinación alta de antigüedad, monto y reincidencia."})
    if recuperable>0: senales.append({"nivel":"atencion","titulo":"Cartera reciente recuperable","texto":f"${recuperable:,.2f} corresponde a vencimientos de hasta 30 días."})
    if not senales: senales.append({"nivel":"saludable","titulo":"Cartera bajo control","texto":"No se detectan señales críticas con la información registrada."})
    return {"total":_money(total),"vencido":_money(vencido),"por_vencer":_money(total-vencido),"recuperable_30":_money(recuperable),"severo":_money(severo),"proyeccion_30":_money(proy),"buckets":list(buckets.values()),"ranking":ranking,"senales":senales,"clientes_prioritarios":sum(1 for x in ranking if x["score"]>=70)}
