from decimal import Decimal, ROUND_HALF_UP
from math import ceil


DEFAULT_RULES = {
    "ph_min": 7.2,
    "ph_max": 7.6,
    "ph_objetivo_normal": 7.4,
    "ph_objetivo_pre_floculacion": 7.8,
    "cloro_min": 1.0,
    "cloro_max": 3.0,
    "cloro_objetivo_normal": 1.5,
    "cloro_objetivo_alto_uso": 2.0,
    "cloro_objetivo_turbidez": 3.0,
    "cloro_objetivo_floculacion": 3.5,
    "cloro_granulado_g_por_m3": 7.0,
    "sulfato_kg_por_tramo": 1.0,
    "sulfato_tramo_m3": 25.0,
    "sulfato_tolerancia_m3": 5.0,
    "alguicida_g_por_25m3": 50.0,
    "p24_g_min_por_25m3": 250.0,
    "p24_g_max_por_25m3": 350.0,
    "seguimiento_horas": 24,
}


def _d(value):
    return Decimal(str(value))


def _round_10(value):
    return int((Decimal(str(value)) / Decimal("10")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 10)


def _cloro_operativo_gramos(volumen, cloro_actual, objetivo, gramos_por_m3=7.0):
    """Dosis operativa JVAQUA para refuerzo/shock; se confirma el objetivo con una nueva medición."""
    if float(cloro_actual) >= float(objetivo):
        return 0
    return max(0, _round_10(float(volumen) * float(gramos_por_m3)))


def _sulfato_kg(volumen, tramo=25.0, tolerancia=5.0):
    # Regla operativa JVAQUA: 20–30 m³ => 1 kg; 31–55 => 2 kg; etc.
    volumen_ajustado = max(float(volumen) - float(tolerancia), 1.0)
    return max(1, int(ceil(volumen_ajustado / float(tramo))))


def _p24_gramos(volumen, ph):
    ph = float(ph)
    if ph < 6.8:
        base = 350
    elif ph < 7.0:
        base = 300
    else:
        base = 250
    return _round_10(base * (float(volumen) / 25.0))


def _alguicida_gramos(volumen):
    return _round_10(50.0 * (float(volumen) / 25.0))


def _producto(nombre, cantidad, unidad, motivo, clave=""):
    return {
        "clave": clave or nombre.lower().replace(" ", "_"),
        "nombre": nombre,
        "cantidad": cantidad,
        "unidad": unidad,
        "motivo": motivo,
    }


def calcular_recomendacion(volumen, ph, cloro, estado_agua, tipo_piscina, reglas=None):
    r = {**DEFAULT_RULES, **(reglas or {})}
    volumen = float(volumen)
    ph = float(ph)
    cloro = float(cloro)
    alto_uso = tipo_piscina in {"condominio", "hotel", "publica"}

    protocolo = []
    productos = []
    advertencias = [
        "No mezclar productos químicos directamente entre sí ni prepararlos juntos en el mismo recipiente.",
        "Aplicar los productos por separado y respetar la ficha técnica y elementos de protección personal.",
        "Volver a medir pH y cloro antes de repetir una corrección.",
    ]
    explicaciones = {
        "sulfato_aluminio": "El sulfato de aluminio es el floculante principal del protocolo JVAQUA. Agrupa partículas para facilitar su sedimentación y además tiende a disminuir el pH.",
        "cloro_granulado": "El cloro granulado se utiliza cuando hace falta una elevación rápida del nivel de desinfectante. La cantidad estimada depende del volumen, el cloro medido y el objetivo del protocolo.",
        "tricloro": "El tricloro en pastilla mantiene el cloro de forma gradual y suele ayudar a que el pH tienda ligeramente hacia abajo. Se prioriza en agua transparente y mantenimiento estable.",
        "metasilicato": "El metasilicato se usa para elevar el pH. Se aplica gradualmente, preferiblemente disuelto, se deja recircular y se vuelve a medir antes de repetir.",
        "p24": "La cal P24/soda en polvo se utiliza como apoyo para elevar el pH antes de una floculación cuando este está bajo, buscando compensar la posterior caída causada por el sulfato.",
        "reductor_ph": "El reductor de pH se reserva para mantenimiento normal cuando el pH está claramente elevado. No se recomienda como paso previo a una floculación con sulfato de aluminio.",
        "alguicida": "En tratamiento de choque se usa como apoyo al control de algas. La referencia operativa JVAQUA es 50 g por cada 25 m³.",
    }

    if estado_agua in {"muy_turbia", "verde"}:
        tipo = "floculacion"
        prioridad = "alta"
        diagnostico = "Tratamiento de choque / floculación"
        resumen = "El estado del agua requiere recuperación mediante floculación. Se recomienda evaluar el resultado después de 24 horas."

        if ph < r["ph_min"]:
            p24 = _p24_gramos(volumen, ph)
            productos.append(_producto("Cal P24 / soda en polvo", p24, "g aprox.", "Subir el pH antes del sulfato, buscando acercarlo aproximadamente a 7.8.", "p24"))
            protocolo.append({"paso": 1, "titulo": "Elevar primero el pH", "detalle": f"El pH está bajo ({ph:.2f}). Aplicar Cal P24/soda en polvo gradualmente. Referencia inicial aproximada: {p24} g para {volumen:.1f} m³. Buscar aproximadamente pH 7.8 antes del sulfato y volver a medir."})
        elif ph > r["ph_max"]:
            protocolo.append({"paso": 1, "titulo": "No aplicar reductor de pH", "detalle": f"El pH está elevado ({ph:.2f}). En este protocolo no se recomienda reductor: el sulfato de aluminio tenderá a disminuirlo durante la floculación."})
        else:
            protocolo.append({"paso": 1, "titulo": "pH apto para iniciar", "detalle": f"El pH actual ({ph:.2f}) permite iniciar el protocolo. Considera que el sulfato tenderá a bajarlo."})

        objetivo_cl = r["cloro_objetivo_floculacion"]
        gramos_cloro = _cloro_operativo_gramos(volumen, cloro, objetivo_cl, r["cloro_granulado_g_por_m3"])
        if gramos_cloro:
            productos.append(_producto("Cloro granulado", gramos_cloro, "g aprox.", f"Shock para llevar el cloro aproximadamente a 3–4 ppm (objetivo de cálculo {objetivo_cl} ppm).", "cloro_granulado"))
        protocolo.append({"paso": 2, "titulo": "Cloración de choque", "detalle": f"Buscar aproximadamente 3–4 ppm de cloro. Referencia operativa JVAQUA de {r['cloro_granulado_g_por_m3']:.1f} g/m³: {gramos_cloro} g; volver a medir para confirmar 3–4 ppm." if gramos_cloro else "El cloro medido ya está dentro o por encima del objetivo de choque. No agregar más sin volver a medir."})

        sulfato = _sulfato_kg(volumen, r["sulfato_tramo_m3"], r["sulfato_tolerancia_m3"])
        productos.append(_producto("Sulfato de aluminio", sulfato, "kg", "Producto principal de la floculación. Regla operativa: 1 kg por cada 25 m³ con tolerancia aproximada de ±5 m³.", "sulfato_aluminio"))
        protocolo.append({"paso": 3, "titulo": "Aplicar sulfato de aluminio", "detalle": f"Aplicar {sulfato} kg como referencia operativa para {volumen:.1f} m³."})

        alguicida = _alguicida_gramos(volumen)
        productos.append(_producto("Alguicida", alguicida, "g aprox.", "Apoyo al tratamiento de choque: 50 g por cada 25 m³.", "alguicida"))
        protocolo.append({"paso": 4, "titulo": "Aplicar alguicida", "detalle": f"Referencia aproximada: {alguicida} g."})
        protocolo.extend([
            {"paso": 5, "titulo": "Dejar flocular", "detalle": "Dejar actuar y sedimentar. Recomendación JVAQUA: 24 horas (el proceso puede observarse desde 12 horas, pero se recomienda completar 24)."},
            {"paso": 6, "titulo": "Aspirar sedimentos", "detalle": "Aspirar cuidadosamente el material sedimentado, preferentemente evitando devolverlo al vaso."},
            {"paso": 7, "titulo": "Retrolavar y recuperar filtración", "detalle": "Realizar retrolavado/limpieza según corresponda y restablecer la filtración."},
            {"paso": 8, "titulo": "Volver a medir", "detalle": "Medir nuevamente pH y cloro y decidir si hace falta una corrección adicional."},
        ])
        advertencias.append("Durante un tratamiento de choque/floculación, mantener la piscina fuera de uso hasta recuperar condiciones adecuadas.")

    elif estado_agua == "ligeramente_turbia":
        tipo = "correctivo"
        prioridad = "media"
        diagnostico = "Mantenimiento correctivo por turbidez ligera"
        resumen = "La piscina no requiere floculación. Se recomienda corregir pH si hace falta, reforzar cloro y mantener filtración."
        paso = 1
        if ph < r["ph_min"]:
            punados = max(1, ceil(volumen / 10.0))
            productos.append(_producto("Metasilicato granulado", punados, "puñado(s) de referencia", "Subir pH gradualmente: aproximadamente un puñado por cada 10 m³, sin aplicar todo de golpe.", "metasilicato"))
            protocolo.append({"paso": paso, "titulo": "Regular pH hacia arriba", "detalle": f"Referencia total máxima inicial: {punados} puñado(s) para {volumen:.1f} m³, pero aplicar gradualmente, disuelto, recircular ~10 minutos y volver a medir antes de repetir."})
            paso += 1
        elif ph > 7.8:
            punados = max(1, ceil(volumen / 25.0))
            productos.append(_producto("Reductor de pH", punados, "puñado(s) de referencia", "El pH está claramente elevado; aplicar gradualmente y volver a medir.", "reductor_ph"))
            protocolo.append({"paso": paso, "titulo": "Reducir pH gradualmente", "detalle": f"Referencia: hasta {punados} puñado(s) por volumen, aplicados gradualmente; esperar recirculación y volver a medir."})
            paso += 1
        else:
            protocolo.append({"paso": paso, "titulo": "Confirmar pH", "detalle": f"pH actual {ph:.2f}. Si está estable, continuar con la corrección de cloro."})
            paso += 1

        objetivo_cl = 3.5 if alto_uso else r["cloro_objetivo_turbidez"]
        gramos_cloro = _cloro_operativo_gramos(volumen, cloro, objetivo_cl, r["cloro_granulado_g_por_m3"])
        if gramos_cloro:
            productos.append(_producto("Cloro granulado", gramos_cloro, "g aprox.", "Refuerzo rápido para turbidez ligera; no se recomienda sulfato en esta condición.", "cloro_granulado"))
        protocolo.append({"paso": paso, "titulo": "Aplicar cloro granulado", "detalle": f"Objetivo orientativo {objetivo_cl:.1f} ppm. Referencia operativa JVAQUA de {r['cloro_granulado_g_por_m3']:.1f} g/m³: {gramos_cloro} g; volver a medir antes de repetir." if gramos_cloro else "El cloro ya está en el objetivo correctivo; no añadir más sin volver a medir."})
        protocolo.append({"paso": paso + 1, "titulo": "Filtrar y volver a medir", "detalle": "Mantener filtración, revisar claridad y volver a medir pH y cloro antes de decidir otra aplicación."})
        if alto_uso:
            advertencias.append("Piscina de alto uso: revisar el cloro con mayor frecuencia; puede requerir aplicaciones más frecuentes o diarias.")

    else:
        tipo = "normal"
        prioridad = "baja" if r["ph_min"] <= ph <= r["ph_max"] and r["cloro_min"] <= cloro <= r["cloro_max"] else "media"
        diagnostico = "Mantenimiento normal"
        resumen = "Agua transparente. Mantener estabilidad del pH y cloro, priorizando tricloro cuando las condiciones lo permitan."
        paso = 1

        if ph < r["ph_min"]:
            punados = max(1, ceil(volumen / 10.0))
            productos.append(_producto("Metasilicato granulado", punados, "puñado(s) de referencia", "Subir el pH progresivamente.", "metasilicato"))
            protocolo.append({"paso": paso, "titulo": "Subir pH gradualmente", "detalle": f"Referencia total: {punados} puñado(s) para {volumen:.1f} m³. Aplicar disuelto y poco a poco; dejar filtrar ~10 minutos, volver a medir y repetir solo si hace falta."})
            paso += 1
        elif ph > 7.8:
            punados = max(1, ceil(volumen / 25.0))
            productos.append(_producto("Reductor de pH", punados, "puñado(s) de referencia", "Reservado para pH claramente elevado.", "reductor_ph"))
            protocolo.append({"paso": paso, "titulo": "Reducir pH", "detalle": f"El pH está claramente elevado ({ph:.2f}). Referencia: {punados} puñado(s), siempre de manera gradual, con recirculación y nueva medición."})
            paso += 1
        elif ph > r["ph_max"]:
            protocolo.append({"paso": paso, "titulo": "pH ligeramente elevado", "detalle": f"pH {ph:.2f}. No usar reductor de inmediato; priorizar tricloro y volver a medir, ya que el pH suele tender a bajar."})
            paso += 1
        else:
            protocolo.append({"paso": paso, "titulo": "pH estable", "detalle": f"Mantener el pH dentro de {r['ph_min']:.1f}–{r['ph_max']:.1f}."})
            paso += 1

        objetivo_cl = r["cloro_objetivo_alto_uso"] if alto_uso else r["cloro_objetivo_normal"]
        if cloro > r["cloro_max"]:
            protocolo.append({"paso": paso, "titulo": "No añadir cloro", "detalle": f"El cloro medido ({cloro:.2f} ppm) está por encima del rango normal. Esperar y volver a medir."})
        elif alto_uso and cloro < objetivo_cl:
            gramos_cloro = _cloro_operativo_gramos(volumen, cloro, objetivo_cl, r["cloro_granulado_g_por_m3"])
            productos.append(_producto("Cloro granulado", gramos_cloro, "g aprox.", "En piscinas de alto uso puede ser necesario un aporte rápido y controles más frecuentes.", "cloro_granulado"))
            protocolo.append({"paso": paso, "titulo": "Reforzar cloro por alta carga", "detalle": f"Buscar alrededor de {objetivo_cl:.1f} ppm y controlar con frecuencia. Estimación inicial de cloro granulado: {gramos_cloro} g."})
        else:
            tabletas = max(1, ceil(volumen / 30.0))
            productos.append(_producto("Tricloro en pastilla", tabletas, "pastilla(s) de 200 g", "Mantenimiento gradual para agua transparente.", "tricloro"))
            protocolo.append({"paso": paso, "titulo": "Mantener con tricloro", "detalle": f"Referencia: {tabletas} pastilla(s) de 200 g para {volumen:.1f} m³, ajustando según mediciones y uso real. Objetivo ideal de cloro: ~{objetivo_cl:.1f} ppm."})
        protocolo.append({"paso": paso + 1, "titulo": "Volver a comprobar", "detalle": "Controlar nuevamente pH y cloro según el uso de la piscina. En alto uso, aumentar la frecuencia de medición y aplicación."})
        if alto_uso:
            advertencias.append("Alto uso: la carga de bañistas puede consumir rápidamente el desinfectante. Se recomienda control frecuente y, cuando sea necesario, aplicaciones diarias.")

    return {
        "diagnostico": diagnostico,
        "tipo_tratamiento": tipo,
        "prioridad": prioridad,
        "resumen": resumen,
        "protocolo": protocolo,
        "productos_sugeridos": productos,
        "explicaciones": explicaciones,
        "advertencias": advertencias,
        "seguimiento_horas": int(r.get("seguimiento_horas", 24)),
        "reglas_usadas": r,
    }

# --- AQUO 2.0 · diagnósticos técnicos guiados ---------------------------------
PROBLEMAS_TECNICOS = {
    "bomba_no_succiona": "La bomba enciende pero no succiona",
    "bomba_no_enciende": "La bomba no enciende",
    "presion_alta": "La presión del filtro está alta",
    "presion_baja": "La presión o el caudal están bajos",
    "aire_circuito": "Hay aire o burbujas en el circuito",
    "fuga_agua": "La piscina pierde agua",
    "filtro_sucio": "El agua no filtra bien",
    "calentador": "Problema con calefacción / bomba de calor",
    "clorador_salino": "Problema con clorador salino",
    "iluminacion": "Problema con iluminación",
    "manchas_incrustaciones": "Manchas o incrustaciones",
    "otro": "Otro problema",
}


def diagnosticar_problema_tecnico(categoria, detalle="", respuestas=None):
    """Orientación segura para problemas no químicos. No sustituye medición eléctrica ni reparación invasiva."""
    respuestas = respuestas or {}
    detalle = (detalle or "").strip()
    base_warn = [
        "No desmontes equipos presurizados ni abras componentes eléctricos energizados.",
        "Si detectas olor a quemado, cables calientes, chispas, fuga eléctrica o riesgo para personas, corta la energía desde un punto seguro y solicita revisión profesional.",
        "Haz una comprobación por vez y conserva la posición original de válvulas antes de cambiarlas.",
    ]
    data = {
        "tipo_tratamiento": "diagnostico_tecnico", "prioridad": "media", "productos_sugeridos": [],
        "explicaciones": {}, "seguimiento_horas": 0, "advertencias": base_warn,
    }
    configs = {
        "bomba_no_succiona": (
            "Pérdida de cebado o restricción en succión",
            "La bomba funciona, pero no consigue mover agua correctamente. Las causas más frecuentes están antes de la bomba: nivel bajo, entrada de aire, canastilla obstruida, válvula cerrada o prefiltro sin agua.",
            [
                ("Verifica el nivel de agua", "El agua debe cubrir adecuadamente el skimmer; si está demasiado baja, puede entrar aire."),
                ("Revisa skimmer y canastilla", "Retira residuos y confirma que la compuerta del skimmer pueda moverse libremente."),
                ("Comprueba las válvulas de succión", "Confirma que la línea que debe alimentar la bomba esté abierta. No cambies varias válvulas a la vez."),
                ("Revisa el prefiltro de la bomba", "Con el equipo apagado y sin presión, comprueba que la canastilla esté limpia y que la tapa/sello estén correctamente asentados."),
                ("Ceba y observa", "Llena el prefiltro según el procedimiento del equipo, cierra correctamente y enciende. Si no recupera caudal o entra aire continuamente, requiere revisión de succión/sellos."),
            ]),
        "bomba_no_enciende": (
            "Falla de alimentación, protección o motor",
            "Si la bomba no enciende, primero hay que diferenciar un problema de programación/alimentación de una falla eléctrica o mecánica del motor.",
            [
                ("Confirma programación y controles", "Verifica que el temporizador o automatización esté ordenando encendido y que no exista un modo OFF."),
                ("Observa sin desmontar", "Comprueba si hay pantalla, alarma, zumbido, olor extraño o disparo de protección."),
                ("No intervengas internamente", "Si hay energía disponible pero el motor no arranca, zumba, se calienta o dispara la protección, detén las pruebas y solicita técnico eléctrico/equipos."),
            ]),
        "presion_alta": (
            "Restricción en filtración",
            "Una presión claramente superior a la presión limpia habitual suele indicar que el filtro o la salida del sistema ofrecen demasiada resistencia.",
            [
                ("Compara con la presión habitual", "La referencia útil es la presión del mismo sistema cuando el filtro está limpio."),
                ("Revisa el retorno", "Confirma que las válvulas de retorno estén en posición correcta y que no exista una obstrucción evidente."),
                ("Limpia el medio filtrante", "En filtro de arena realiza retrolavado/enjuague cuando corresponda; en cartucho, limpia el elemento siguiendo el fabricante."),
                ("Vuelve a medir", "Si la presión continúa anormalmente alta después de limpiar, evita forzar el sistema y solicita revisión del filtro/multiválvula/tubería."),
            ]),
        "presion_baja": (
            "Caudal insuficiente o restricción en succión",
            "Presión y caudal bajos suelen apuntar a falta de agua hacia la bomba, obstrucción antes de ella, entrada de aire o pérdida de rendimiento.",
            [
                ("Revisa nivel y skimmer", "Confirma nivel suficiente y elimina residuos de skimmer/canastillas."),
                ("Observa el prefiltro", "Si ves aire persistente, busca una entrada de aire en tapa, uniones o línea de succión."),
                ("Comprueba válvulas", "Verifica que las líneas necesarias estén abiertas."),
                ("Escala si persiste", "Si el circuito está libre y el caudal sigue bajo, puede existir obstrucción interna o problema de impulsor/bomba que requiere revisión técnica."),
            ]),
        "aire_circuito": (
            "Entrada de aire en el lado de succión",
            "Burbujas persistentes en el prefiltro o retornos suelen indicar que el sistema está aspirando aire antes de la bomba o que el nivel de agua es insuficiente.",
            [
                ("Comprueba el nivel", "Evita que el skimmer forme remolino y aspire aire."),
                ("Revisa tapa y sello del prefiltro", "Con el equipo apagado, limpia superficies de cierre y comprueba que el sello esté correctamente colocado."),
                ("Revisa uniones y válvulas visibles", "Busca conexiones flojas o señales de entrada de aire sin desmontar la instalación."),
                ("Observa después del cebado", "Si las burbujas regresan continuamente, solicita prueba específica de la línea de succión."),
            ]),
        "fuga_agua": (
            "Pérdida de agua por confirmar",
            "Antes de asumir una fuga estructural hay que separar evaporación, salpicaduras y pérdidas asociadas al sistema de filtración.",
            [
                ("Marca el nivel", "Registra el nivel y compáralo durante un periodo sin reposición automática."),
                ("Inspecciona equipos y desagües", "Busca humedad en bomba, filtro, uniones, válvula selectora y línea de desagüe."),
                ("Compara equipo encendido/apagado", "Si la pérdida cambia mucho según opere la bomba, esa diferencia orienta hacia tubería/equipos."),
                ("Solicita prueba de fuga", "Si la pérdida es sostenida y supera lo esperable, requiere diagnóstico de estanqueidad; evita romper superficies sin localizar primero la fuga."),
            ]),
        "filtro_sucio": (
            "Filtración insuficiente",
            "Si el agua no aclara aunque la química sea razonable, hay que comprobar caudal, presión, tiempo de filtración y condición del medio filtrante.",
            [
                ("Comprueba circulación", "Confirma que exista caudal perceptible en retornos y que la bomba permanezca cebada."),
                ("Lee el manómetro", "Compara la presión con el valor habitual del filtro limpio."),
                ("Limpia el filtro", "Realiza el procedimiento adecuado al tipo de filtro y vuelve a comprobar presión/caudal."),
                ("Evalúa el medio filtrante", "Si el rendimiento sigue siendo pobre, revisa condición de arena/cartucho y posibles canales, roturas u obstrucciones."),
            ]),
        "calentador": (
            "Calefacción sin rendimiento o con bloqueo",
            "Una bomba de calor o calentador puede dejar de calentar por falta de flujo, consigna/configuración, condiciones ambientales o una alarma propia del equipo.",
            [
                ("Confirma flujo de agua", "Muchos equipos bloquean calefacción cuando el caudal es insuficiente."),
                ("Revisa consigna y modo", "Comprueba temperatura objetivo, modo de operación y temporización."),
                ("Registra la alarma", "Si aparece un código, anótalo junto con marca/modelo para consultar el manual correspondiente."),
                ("No abras el equipo", "Problemas de refrigerante, gas, resistencias o electricidad requieren servicio calificado."),
            ]),
        "clorador_salino": (
            "Producción de cloro insuficiente o alarma del clorador",
            "El clorador depende de flujo, salinidad, estado de la celda y configuración. Una alarma no significa automáticamente que la celda esté dañada.",
            [
                ("Comprueba circulación", "Verifica que exista flujo suficiente y que no haya alarma de FLOW."),
                ("Revisa salinidad y configuración", "Compara la lectura con el rango indicado por el fabricante del equipo."),
                ("Inspecciona la celda según manual", "Busca incrustación visible y sigue únicamente el procedimiento de limpieza del fabricante."),
                ("Mide el agua", "Confirma cloro real con un kit; no dependas solo del porcentaje mostrado por el equipo."),
            ]),
        "iluminacion": (
            "Falla de iluminación que requiere enfoque eléctrico seguro",
            "La iluminación de piscina combina electricidad y agua. AQUO puede ayudarte a identificar síntomas, pero no debe guiar reparaciones eléctricas internas al propietario.",
            [
                ("Identifica el alcance", "Comprueba si falla una sola luminaria o todo el circuito y si el control/automatización responde."),
                ("No manipules conexiones energizadas", "No abras cajas, nichos, transformadores ni luminarias con energía aplicada."),
                ("Solicita revisión calificada", "Si la protección dispara, hay humedad, parpadeos anormales o ausencia de alimentación, requiere electricista/técnico de piscina calificado."),
            ]),
        "manchas_incrustaciones": (
            "Depósitos minerales o manchas por identificar",
            "El color, textura y ubicación ayudan a diferenciar incrustación cálcica, metales y material orgánico. No conviene aplicar ácidos o removedores sin identificar primero la causa.",
            [
                ("Describe color y textura", "Indica si es blanca/áspera, marrón/rojiza, verdosa, negra u orgánica y dónde aparece."),
                ("Mide el agua", "pH y, cuando sea posible, alcalinidad/dureza ayudan a interpretar depósitos minerales."),
                ("Evita tratamientos agresivos a ciegas", "No apliques ácido concentrado ni productos para metales sin confirmar compatibilidad con el acabado."),
                ("Documenta con fotografías", "Una imagen del acabado y la mancha permite orientar mejor una revisión profesional."),
            ]),
        "otro": (
            "Caso técnico por precisar",
            "AQUO necesita algunos detalles adicionales para clasificar correctamente el problema y evitar recomendar una acción que no corresponda.",
            [
                ("Describe el síntoma", "Indica qué equipo o parte de la piscina está afectada, qué ocurre y desde cuándo."),
                ("Indica qué cambió", "Menciona mantenimiento reciente, cortes de energía, lluvias, reparaciones o productos aplicados."),
                ("Registra señales", "Anota ruidos, alarmas, presión, caudal, fugas o cualquier cambio visible."),
                ("Evita intervenir si hay riesgo", "Ante electricidad, presión, gas, productos incompatibles o daño estructural, detén la intervención y solicita un profesional."),
            ]),
    }
    diag, resumen, pasos = configs.get(categoria, configs["otro"])
    if detalle:
        resumen += f" Información reportada: {detalle[:500]}"
    data.update({
        "diagnostico": diag,
        "resumen": resumen,
        "protocolo": [{"paso": i, "titulo": t, "detalle": d} for i, (t, d) in enumerate(pasos, 1)],
    })
    if categoria in {"bomba_no_enciende", "iluminacion"}:
        data["prioridad"] = "alta"
    return data
