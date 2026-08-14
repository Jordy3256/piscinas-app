from django.db import migrations, models
from django.utils import timezone


def seed_curso(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    Consejo = apps.get_model('asistente_tecnico', 'ConsejoJVAQUA')

    def upsert(codigo, **data):
        defaults = {
            'tipo': data.pop('tipo', 'biblioteca'),
            'slug': data.pop('slug'),
            'titulo': data.pop('titulo'),
            'resumen': data.pop('resumen', ''),
            'nivel': data.pop('nivel', 'basico'),
            'tiempo_lectura_min': data.pop('tiempo_lectura_min', 6),
            'estado': data.pop('estado', 'aprobado'),
            'version': data.pop('version', '1.0'),
            'acceso': data.pop('acceso', 'compartido'),
            'modulo_curso': data.pop('modulo_curso', ''),
            'orden_curso': data.pop('orden_curso', 0),
            'orden': data.pop('orden', 0),
            'introduccion': data.pop('introduccion', ''),
            'contenido': data.pop('contenido', ''),
            'procedimiento': data.pop('procedimiento', ''),
            'herramientas_materiales': data.pop('herramientas_materiales', ''),
            'funcionamiento': data.pop('funcionamiento', ''),
            'componentes': data.pop('componentes', ''),
            'mantenimiento': data.pop('mantenimiento', ''),
            'fallas_frecuentes': data.pop('fallas_frecuentes', ''),
            'buenas_practicas': data.pop('buenas_practicas', ''),
            'errores_comunes': data.pop('errores_comunes', ''),
            'recomendaciones_jvaqua': data.pop('recomendaciones_jvaqua', ''),
            'referencias_tecnicas': data.pop('referencias_tecnicas', ''),
            'etiquetas': data.pop('etiquetas', ''),
        }
        obj, _ = Contenido.objects.update_or_create(codigo=codigo, defaults=defaults)
        return obj

    # Los cinco artículos químicos ya revisados por JVAQUA pasan a conocimiento oficial y al curso.
    existentes = {
        'BT-Q-001': ('productos', 10),
        'BT-Q-002': ('productos', 20),
        'BT-Q-003': ('productos', 30),
        'BT-Q-004': ('productos', 40),
        'BT-Q-005': ('productos', 50),
    }
    for codigo, (modulo, orden) in existentes.items():
        Contenido.objects.filter(codigo=codigo).update(
            estado='aprobado', version='1.0', acceso='compartido',
            modulo_curso=modulo, orden_curso=orden,
            aprobado_en=timezone.now(),
        )

    refs_quimica = (
        'Referencias de contraste: CDC Healthy Swimming (tratamiento y pruebas de piscinas); '
        'PHTA fact sheets sobre química del agua. Las metas operativas JVAQUA prevalecen para el trabajo interno.'
    )
    refs_seguridad = (
        'Referencias de contraste: CDC Pool Chemical Safety y MMWR sobre lesiones por químicos de piscina; '
        'EPA Chemical Safety Alert sobre almacenamiento y manipulación de químicos.'
    )
    refs_equipos = (
        'Referencias de contraste: manuales oficiales Pentair y Hayward para bombas, filtros de arena y válvulas multipuerto. '
        'Siempre prevalece el manual del modelo instalado.'
    )

    items = [
        dict(codigo='AC-F-001', titulo='Cómo funciona una piscina', slug='como-funciona-una-piscina', modulo_curso='fundamentos', orden_curso=10,
             resumen='Comprende el recorrido del agua y la función conjunta de succión, bomba, filtro, retornos y tratamiento químico.',
             introduccion='Una piscina se mantiene estable cuando circulación, filtración y tratamiento químico trabajan juntos. Aprender el recorrido del agua permite entender por qué una falla en un solo componente puede afectar toda la piscina.',
             contenido='RECORRIDO BÁSICO\n1. El agua entra por skimmers, drenajes u otras líneas de succión.\n2. Llega a la bomba.\n3. La bomba impulsa el agua hacia el filtro.\n4. El filtro retiene partículas.\n5. El agua regresa por los retornos.\n6. El tratamiento químico controla microorganismos y mantiene condiciones adecuadas.\n\nUn agua visualmente limpia no garantiza por sí sola que esté correctamente desinfectada.',
             buenas_practicas='• Antes de aplicar químicos, confirma que existe circulación adecuada.\n• Aprende a reconocer dónde están succión, bomba, filtro, válvulas y retornos.\n• Observa siempre el caudal y el estado general del sistema.',
             errores_comunes='• Pensar que el filtro sustituye al cloro.\n• Pensar que el cloro sustituye a la filtración.\n• Aplicar tratamientos sin comprobar que el sistema mueve agua correctamente.',
             recomendaciones_jvaqua='En JVAQUA, toda visita comienza con inspección del equipo y estado del agua antes de limpiar o dosificar.',
             referencias_tecnicas='CDC Healthy Swimming: operación, desinfección, recirculación y filtración deben mantenerse de forma conjunta.', etiquetas='fundamentos,circulacion,filtracion,bomba,filtro,retornos'),
        dict(codigo='AC-F-002', titulo='Circulación y filtración', slug='circulacion-y-filtracion', modulo_curso='fundamentos', orden_curso=20,
             resumen='Aprende por qué mover y filtrar correctamente el agua es esencial para que el tratamiento químico funcione de manera uniforme.',
             contenido='La circulación distribuye desinfectante y conduce partículas hacia el sistema de filtración. La filtración retira material suspendido, pero no reemplaza la desinfección. Una circulación deficiente puede dejar zonas con menor renovación de agua y favorecer problemas.',
             funcionamiento='La bomba crea el flujo. El filtro añade resistencia y captura partículas. La presión del filtro y el caudal observado ayudan a reconocer cambios en el sistema. Una presión que aumenta respecto a la referencia limpia puede indicar que el filtro necesita limpieza o retrolavado, según el tipo y el manual.',
             buenas_practicas='• Conoce la presión normal del filtro cuando está limpio.\n• Mantén canastillas libres de residuos.\n• Comprueba que exista retorno de agua.\n• No manipules válvulas multipuerto con la bomba funcionando.',
             errores_comunes='• Retrolavar por rutina sin observar necesidad.\n• Operar con canastillas completamente obstruidas.\n• Cambiar posiciones de válvula con la bomba encendida.', referencias_tecnicas=refs_equipos, etiquetas='circulacion,filtracion,presion,caudal,retorno'),
        dict(codigo='AC-F-003', titulo='Cómo medir pH y cloro correctamente', slug='medicion-ph-cloro', modulo_curso='fundamentos', orden_curso=30,
             resumen='Una recomendación química solo es tan buena como la medición que la origina.',
             procedimiento='1. Toma la muestra en agua representativa, evitando una zona donde acabas de aplicar producto.\n2. Usa el kit según sus instrucciones y recipientes limpios.\n3. Lee pH y cloro con buena iluminación.\n4. Registra los valores reales.\n5. Si una lectura parece imposible, repite antes de dosificar.\n6. Después de una corrección gradual, deja circular y vuelve a medir cuando corresponda.',
             buenas_practicas='• Enjuaga el comparador con agua de la piscina antes de la prueba.\n• Mantén reactivos en buen estado y revisa vencimiento.\n• Evita contaminar tapas, celdas o goteros con químicos.',
             errores_comunes='• Estimar el color sin respetar instrucciones del kit.\n• Medir inmediatamente junto al punto de dosificación.\n• Ajustar varios parámetros sin volver a medir.', recomendaciones_jvaqua='El checklist operativo JVAQUA utiliza pH y CL como mediciones de campo principales. Rango operativo interno: pH 7,2–7,6 y CL 1–3 ppm.', referencias_tecnicas=refs_quimica, etiquetas='medicion,ph,cloro,test,dpd,kit'),

        dict(codigo='AC-Q-001', titulo='pH: qué significa y cómo interpretarlo', slug='ph-piscina', modulo_curso='quimica', orden_curso=10,
             resumen='El pH influye en confort, protección de equipos y comportamiento químico del agua.',
             introduccion='El pH expresa qué tan ácida o básica es el agua. En operación JVAQUA se busca normalmente 7,2–7,6.',
             contenido='PH BAJO\nPuede aumentar la agresividad del agua hacia materiales y generar incomodidad.\n\nPH ALTO\nPuede favorecer incrustaciones, turbidez y dificultar el control del agua.\n\nNo corrijas pH por intuición. Mide, corrige en etapas y vuelve a medir.',
             buenas_practicas='• Ajusta de forma gradual.\n• Considera el tipo de tratamiento que viene después.\n• En floculación JVAQUA, recuerda que el sulfato de aluminio tiende a bajar el pH.',
             errores_comunes='• Intentar dejar una cifra exacta con una sola dosis grande.\n• Aplicar reductor automáticamente durante una floculación con pH alto sin considerar el efecto del sulfato.', recomendaciones_jvaqua='Meta operativa JVAQUA: 7,2–7,6. Para una floculación con pH bajo, puede elevarse aproximadamente hacia 7,8 antes del sulfato.', referencias_tecnicas=refs_quimica, etiquetas='ph,acidez,basicidad,equilibrio,agua'),
        dict(codigo='AC-Q-002', titulo='Cloro libre', slug='cloro-libre', modulo_curso='quimica', orden_curso=20,
             resumen='El cloro libre es la fracción disponible para desinfectar el agua y debe interpretarse junto con pH, uso de estabilizante y demanda de la piscina.',
             contenido='El cloro se consume al reaccionar con contaminantes y por exposición ambiental. Una lectura baja puede indicar que el agua está demandando más desinfectante; una lectura por sí sola no explica la causa. El uso de productos estabilizados requiere considerar también el ácido cianúrico.',
             buenas_practicas='• Mide antes de dosificar.\n• Registra la lectura inicial y final cuando corresponda.\n• Considera carga de bañistas, sol, lluvia y estado del agua.',
             errores_comunes='• Dosificar siempre la misma cantidad sin medir.\n• Confundir olor fuerte con “demasiado cloro” sin analizar el agua.\n• Ignorar el efecto del estabilizante en piscinas que usan tricloro/dicloro.', recomendaciones_jvaqua='Rango operativo interno JVAQUA: 1–3 ppm. En choque, el Asistente puede recomendar elevar temporalmente a aproximadamente 3–4 ppm según el caso.', referencias_tecnicas=refs_quimica, etiquetas='cloro libre,desinfeccion,ppm,cloro'),
        dict(codigo='AC-Q-003', titulo='Alcalinidad total', slug='alcalinidad-total', modulo_curso='quimica', orden_curso=30, nivel='intermedio',
             resumen='Aunque no forma parte del checklist rutinario JVAQUA, entender la alcalinidad ayuda a comprender por qué algunas piscinas tienen un pH difícil de estabilizar.',
             contenido='La alcalinidad representa principalmente la capacidad tampón del agua frente a cambios de pH. Valores inadecuados pueden contribuir a inestabilidad del pH o a tendencias de incrustación/corrosión dependiendo del resto de la química.',
             buenas_practicas='• Trátala como un parámetro de diagnóstico avanzado, no como una medición obligatoria de cada visita.\n• Evalúala cuando el pH se comporta de manera anormal o recurrente.', errores_comunes='• Ajustar alcalinidad sin considerar pH y el resto del balance.\n• Convertirla en una tarea rutinaria innecesaria para todos los mantenimientos.', referencias_tecnicas='PHTA fact sheets sobre química del agua y balance; consultar límites del estándar aplicable a cada instalación.', etiquetas='alcalinidad,tac,balance,ph'),
        dict(codigo='AC-Q-004', titulo='Ácido cianúrico (CYA)', slug='acido-cianurico-cya', modulo_curso='quimica', orden_curso=40, nivel='intermedio',
             resumen='El estabilizante protege al cloro de la radiación solar, pero una acumulación excesiva modifica la forma en que debe interpretarse el cloro libre.',
             contenido='El ácido cianúrico puede añadirse directamente o acumularse por el uso de cloros estabilizados como tricloro y dicloro. Su función es reducir la degradación del cloro por la luz solar. El exceso puede obligar a trabajar con un residual de cloro diferente y complicar el control del agua.',
             buenas_practicas='• Revisa CYA periódicamente en piscinas exteriores con uso sostenido de tricloro/dicloro.\n• Si el cloro parece poco efectivo pese a dosificaciones repetidas, considera medir CYA como parte del diagnóstico.', errores_comunes='• Añadir estabilizante sin medir.\n• Usar tricloro indefinidamente sin considerar la acumulación de CYA.', referencias_tecnicas='CDC Healthy Swimming: cuando se usa CYA o cloro estabilizado, recomienda considerar un mínimo de cloro libre mayor. PHTA: CYA estabiliza el cloro frente a la luz solar.', etiquetas='cya,acido cianurico,estabilizante,tricloro'),
        dict(codigo='AC-Q-005', titulo='Dureza cálcica', slug='dureza-calcica', modulo_curso='quimica', orden_curso=50, nivel='intermedio',
             resumen='La dureza cálcica forma parte del balance del agua y ayuda a evaluar tendencias de incrustación o agresividad.',
             contenido='La dureza cálcica mide calcio disuelto. No se interpreta de forma aislada: pH, alcalinidad, temperatura y otros factores determinan la tendencia general del agua. Es especialmente relevante ante incrustaciones persistentes, superficies cementicias o agua agresiva.',
             buenas_practicas='• Úsala como parámetro de diagnóstico y balance periódico.\n• Evita corregirla sin identificar primero la tendencia general del agua.', errores_comunes='• Confundir dureza con alcalinidad.\n• Tratar cualquier depósito blanco como problema de dureza sin confirmar.', referencias_tecnicas='PHTA material técnico sobre balance del agua e índice de saturación.', etiquetas='dureza calcio,incrustacion,balance'),

        dict(codigo='BT-Q-006', titulo='Hipoclorito de sodio (cloro líquido)', slug='hipoclorito-de-sodio', modulo_curso='productos', orden_curso=60,
             resumen='Fuente líquida de cloro no estabilizado. Su concentración y envejecimiento influyen directamente en la dosis.',
             contenido='El hipoclorito de sodio aporta cloro disponible sin añadir ácido cianúrico. Es alcalino y pierde concentración con el tiempo, especialmente por calor y almacenamiento inadecuado. La dosis debe calcularse según concentración real del producto y lectura de la piscina.',
             procedimiento='1. Mide pH y cloro.\n2. Confirma la concentración indicada en la etiqueta.\n3. Calcula la cantidad necesaria.\n4. Añade según instrucciones del fabricante, con circulación adecuada y evitando salpicaduras.\n5. No mezcles con ácidos ni con otros químicos concentrados.', buenas_practicas='• Almacena en lugar fresco y ventilado.\n• Rota inventario: el producto envejece.\n• Utiliza recipientes compatibles y etiquetados.', errores_comunes='• Usar una dosis calculada para otra concentración.\n• Mezclar con ácido.\n• Guardar a alta temperatura o bajo sol directo.', referencias_tecnicas=refs_seguridad, etiquetas='hipoclorito sodio,cloro liquido,desinfeccion'),
        dict(codigo='BT-Q-007', titulo='Reductor de pH (ácido seco / ácido)', slug='reductor-de-ph', modulo_curso='productos', orden_curso=70,
             resumen='Producto para reducir pH cuando realmente está por encima del objetivo. Debe dosificarse de manera gradual y segura.',
             contenido='Los reductores pueden ser productos secos (por ejemplo bisulfatos) o ácidos líquidos. La concentración y forma de aplicación dependen del producto. La seguridad es crítica: nunca deben mezclarse con productos clorados.',
             procedimiento='1. Confirma pH alto con una medición válida.\n2. Determina volumen y producto exacto.\n3. Sigue la dosis de etiqueta o el cálculo del Asistente.\n4. Aplica siguiendo la etiqueta y con protección adecuada.\n5. Deja circular y vuelve a medir antes de repetir.', buenas_practicas='• Ajusta en etapas.\n• Mantén ácidos separados de cloros.\n• Usa EPP indicado por la FDS.', errores_comunes='• Corregir sin medir.\n• Mezclar ácido y cloro.\n• Usar reductor durante una floculación JVAQUA sin considerar que el sulfato ya reducirá el pH.', referencias_tecnicas=refs_seguridad, etiquetas='reductor ph,acido,ph alto'),
        dict(codigo='BT-Q-008', titulo='Incrementador de pH', slug='incrementador-de-ph', modulo_curso='productos', orden_curso=80,
             resumen='Familia de productos alcalinos utilizados para elevar pH. La dosis depende de la formulación y del comportamiento real del agua.',
             contenido='No todos los elevadores de pH tienen la misma composición. Carbonato de sodio, metasilicato y otros productos alcalinos tienen concentraciones y efectos distintos. Por eso JVAQUA conserva una ficha separada de Metasilicato y exige identificar el producto antes de dosificar.',
             procedimiento='Mide → aplica en etapas → deja circular → vuelve a medir. No trates una referencia de “puñados” como una dosis universal entre productos.', buenas_practicas='• Identifica el producto.\n• Evita aplicar concentrado sobre acabados sensibles.\n• Mantén utensilios secos.', errores_comunes='• Usar las mismas cantidades para distintas formulaciones.\n• Repetir dosis sin retest.', referencias_tecnicas=refs_quimica, etiquetas='incrementador ph,ph bajo,alcalino'),
        dict(codigo='BT-Q-009', titulo='Clarificante', slug='clarificante-piscina', modulo_curso='productos', orden_curso=90,
             resumen='Auxiliar para mejorar la captura de partículas finas cuando el agua presenta turbidez leve y la filtración está funcionando.',
             contenido='Los clarificantes agrupan o modifican partículas pequeñas para facilitar su retención por el filtro. No sustituyen el balance, desinfección ni una floculación cuando el problema requiere sedimentación completa.',
             buenas_practicas='• Usa solo cuando el filtro está en condiciones de trabajar.\n• Sigue la dosis específica del producto.\n• Distingue clarificación de floculación.', errores_comunes='• Sobredosificar.\n• Usar clarificante para intentar resolver agua verde severa.\n• Aplicarlo sin revisar filtración.', referencias_tecnicas='Seguir etiqueta y ficha técnica del fabricante del clarificante utilizado por JVAQUA.', etiquetas='clarificante,turbidez,filtracion'),

        dict(codigo='PR-M-001', tipo='procedimiento', titulo='Inspección inicial del mantenimiento', slug='inspeccion-inicial-mantenimiento', modulo_curso='mantenimiento', orden_curso=10,
             resumen='Antes de limpiar o dosificar, el técnico debe entender qué está ocurriendo en la piscina y en su sistema.',
             procedimiento='1. Observa estado general del agua.\n2. Comprueba nivel de agua.\n3. Revisa visualmente bomba y filtro.\n4. Observa fugas, ruidos, aire visible o presión anormal.\n5. Mide pH y cloro.\n6. Identifica novedades que deban reportarse.\n7. Solo después continúa con limpieza y tratamiento.', herramientas_materiales='Kit de pH/CL, teléfono con JVAQUA ERP y elementos básicos de inspección.', buenas_practicas='• No omitas una anomalía porque la piscina “se ve limpia”.\n• Documenta novedades importantes antes de intervenir.', errores_comunes='• Comenzar aspirando sin inspeccionar.\n• Aplicar químicos antes de medir.\n• Ignorar una bomba sin cebado o una fuga evidente.', recomendaciones_jvaqua='La inspección es el primer paso oficial del mantenimiento JVAQUA.', etiquetas='inspeccion,checklist,mantenimiento'),
        dict(codigo='PR-M-002', tipo='procedimiento', titulo='Aspirado de piscina', slug='aspirado-piscina', modulo_curso='mantenimiento', orden_curso=20,
             resumen='Retira sedimentos del fondo sin dispersarlos y sin comprometer el funcionamiento de la bomba.',
             procedimiento='1. Revisa cuánto sedimento existe y decide si corresponde filtrar o aspirar a desagüe.\n2. Monta aspiradora, manguera y pértiga.\n3. Llena la manguera de agua para evitar introducir aire.\n4. Conecta el sistema de succión.\n5. Aspira con movimientos lentos y ordenados, evitando levantar sedimento.\n6. Vigila succión y nivel de agua.\n7. Al terminar, limpia canastillas y normaliza válvulas si se modificaron.', herramientas_materiales='Pértiga, cabezal de aspirado, manguera, adaptadores necesarios.', buenas_practicas='• Mueve el cabezal lentamente.\n• Si aspiras a desagüe, vigila el nivel de agua.\n• Evita que la bomba succione aire.', errores_comunes='• Conectar una manguera llena de aire.\n• Aspirar demasiado rápido.\n• Olvidar devolver la válvula a la posición normal.', etiquetas='aspirado,limpieza,fondo'),
        dict(codigo='PR-M-003', tipo='procedimiento', titulo='Cepillado de paredes y piso', slug='cepillado-piscina', modulo_curso='mantenimiento', orden_curso=30,
             resumen='Desprende suciedad y biofilm de superficies para facilitar su eliminación y prevenir acumulaciones.',
             procedimiento='1. Elige cepillo adecuado para el acabado.\n2. Cepilla paredes, esquinas, escalones, banquetas y piso.\n3. Trabaja de arriba hacia abajo y empuja residuos hacia zonas donde puedan aspirarse o circular.\n4. Refuerza zonas con poca circulación y línea de agua.', buenas_practicas='• Usa cepillo compatible con el revestimiento.\n• No olvides esquinas, escaleras y zonas de sombra.', errores_comunes='• Usar cepillos abrasivos sobre superficies sensibles.\n• Cepillar solo las zonas visibles.', etiquetas='cepillado,paredes,piso,biofilm'),
        dict(codigo='PR-M-004', tipo='procedimiento', titulo='Recolección de basura y limpieza superficial', slug='recoleccion-basura-piscina', modulo_curso='mantenimiento', orden_curso=40,
             resumen='Retira hojas, insectos y residuos antes de que lleguen al sistema o se depositen en el fondo.',
             procedimiento='Recorre la superficie con la red, limpia residuos flotantes y revisa puntos de acumulación. Cuando exista carga alta de hojas, retírala antes del aspirado para evitar obstrucciones.', buenas_practicas='• Vacía la red con frecuencia.\n• Revisa también skimmer y canastillas.', errores_comunes='• Empujar basura hacia el drenaje.\n• Dejar residuos grandes para que los capture el sistema.', etiquetas='basura,red,hojas,superficie'),
        dict(codigo='PR-M-005', tipo='procedimiento', titulo='Limpieza del filtro/canastilla de bomba', slug='limpieza-canastilla-bomba', modulo_curso='mantenimiento', orden_curso=50,
             resumen='Una canastilla obstruida reduce caudal y puede dificultar el cebado de la bomba.',
             procedimiento='1. Detén la bomba antes de abrir.\n2. Asegura condiciones seguras y libera presión según el sistema.\n3. Abre la tapa.\n4. Retira la canastilla y elimina residuos sin golpearla.\n5. Revisa sello/O-ring y asiento de tapa.\n6. Llena el prefiltro con agua si el sistema necesita cebado.\n7. Cierra correctamente, abre líneas necesarias y reinicia observando el cebado.', buenas_practicas='• Mantén el O-ring limpio.\n• Observa si entra aire después de cerrar.\n• Nunca dejes la bomba funcionando en seco.', errores_comunes='• Abrir el prefiltro con la bomba encendida.\n• Golpear la canastilla.\n• Arrancar sin agua o con válvulas cerradas.', referencias_tecnicas='Pentair y Hayward: no operar la bomba en seco; limpiar regularmente la canastilla y asegurar un cebado correcto.', etiquetas='bomba,canastilla,prefiltro,cebado'),
        dict(codigo='PR-M-006', tipo='procedimiento', titulo='Retrolavado y enjuague de filtro de arena', slug='retrolavado-enjuague-filtro-arena', modulo_curso='mantenimiento', orden_curso=60,
             resumen='Limpia el medio filtrante invirtiendo el flujo y luego asienta la arena antes de volver a filtrar.',
             procedimiento='1. APAGA la bomba.\n2. Coloca la multiválvula en BACKWASH/RETROLAVADO.\n3. Enciende la bomba y observa el agua de descarga; mantén el ciclo según el equipo y hasta que salga limpia.\n4. APAGA la bomba.\n5. Coloca la válvula en RINSE/ENJUAGUE.\n6. Enciende brevemente según el manual para asentar el medio y limpiar la válvula.\n7. APAGA la bomba.\n8. Regresa a FILTER/FILTRAR.\n9. Enciende y comprueba presión y funcionamiento.', buenas_practicas='• Siempre apaga la bomba antes de mover la multiválvula.\n• Usa la mirilla/descarga como referencia además del tiempo.\n• Conoce la presión limpia del filtro.', errores_comunes='• Mover la multiválvula con la bomba encendida.\n• Omitir el enjuague.\n• Retrolavar sin necesidad de forma excesiva.', referencias_tecnicas='Pentair Triton/Tagelus y Hayward ProSeries: apagar la bomba antes de cambiar la posición de la válvula; retrolavar hasta descarga limpia y realizar enjuague según manual.', etiquetas='retrolavado,backwash,rinse,enjuague,filtro arena,multivalvula'),
        dict(codigo='PR-M-007', tipo='procedimiento', titulo='Limpieza de filos y línea de agua', slug='limpieza-filos-linea-agua', modulo_curso='mantenimiento', orden_curso=70,
             resumen='Evita acumulación de grasa, suciedad y marcas en el perímetro de la piscina.',
             procedimiento='Utiliza herramienta y limpiador compatible con el acabado. Trabaja por secciones, evita arrojar residuos concentrados al agua y enjuaga cuando el producto lo requiera.', buenas_practicas='• Prueba productos nuevos en una zona pequeña.\n• Usa esponjas compatibles con el revestimiento.', errores_comunes='• Utilizar abrasivos o ácidos sin confirmar compatibilidad.\n• Dejar producto concentrado secándose sobre el acabado.', etiquetas='filos,linea agua,limpieza,acabado'),
        dict(codigo='PR-M-008', tipo='procedimiento', titulo='Floculación JVAQUA con sulfato de aluminio', slug='floculacion-jvaqua-sulfato', modulo_curso='mantenimiento', orden_curso=80, nivel='intermedio',
             resumen='Protocolo JVAQUA para agua muy turbia o verde cuando se necesita coagular y sedimentar partículas para aspirarlas posteriormente.',
             procedimiento='1. Confirma que realmente corresponde floculación: agua muy turbia o verde.\n2. Mide pH y cloro.\n3. Si pH está bajo, elévalo aproximadamente hacia 7,8 antes del sulfato.\n4. Si pH está alto, JVAQUA normalmente no añade reductor porque el sulfato tenderá a bajarlo.\n5. Realiza el shock de cloro según el Asistente (objetivo operativo aproximado 3–4 ppm).\n6. Aplica sulfato de aluminio. Referencia JVAQUA: aproximadamente 1 kg por 25 m³ (tolerancia operativa ±5 m³, revisar caso).\n7. Deja sedimentar preferentemente alrededor de 24 h; rango operativo aceptado 12–24 h.\n8. Aspira el sedimento a desagüe cuando corresponda.\n9. Retrolava/enjuaga y restablece filtración.\n10. Vuelve a medir pH y cloro.', buenas_practicas='• No confundas floculación con mantenimiento rutinario.\n• Informa que la piscina no debe usarse durante el proceso.\n• Aspira el sedimento lentamente.', errores_comunes='• Flocular agua transparente.\n• Agregar reductor de pH automáticamente con pH alto.\n• Poner en suspensión el sedimento al aspirar.\n• Considerar 12 h como objetivo cuando puede dejarse 24 h.', recomendaciones_jvaqua='Sulfato es el producto principal obligatorio del protocolo de floculación JVAQUA. Usa el Asistente para ajustar el caso real.', etiquetas='floculacion,sulfato,agua verde,agua turbia,shock'),
        dict(codigo='PR-M-009', tipo='procedimiento', titulo='Cierre correcto del mantenimiento', slug='cierre-mantenimiento-jvaqua', modulo_curso='mantenimiento', orden_curso=90, acceso='interno',
             resumen='El trabajo no termina hasta que la piscina queda operativa, el área ordenada y el mantenimiento registrado correctamente.',
             procedimiento='1. Confirma que válvulas y filtración quedaron en posición normal.\n2. Verifica el área y retira herramientas/residuos.\n3. Revisa visualmente el resultado.\n4. Realiza medición final cuando corresponda.\n5. Completa checklist.\n6. Sube las fotografías obligatorias: antes, después y pH/CL finales.\n7. Registra novedades y consumos cuando apliquen.\n8. Finaliza el mantenimiento en JVAQUA ERP.', buenas_practicas='• No cierres el mantenimiento desde el vehículo si falta información que debías verificar en sitio.\n• Comprueba que no dejas válvulas en WASTE/BACKWASH.', errores_comunes='• Finalizar sin revisar posición del sistema.\n• Fotografías poco claras.\n• Omitir una novedad importante.', recomendaciones_jvaqua='Este procedimiento es interno y forma parte del estándar operativo de JVAQUA.', etiquetas='cierre,erp,fotografias,checklist'),

        dict(codigo='EQ-001', tipo='equipo', titulo='Bomba de piscina', slug='bomba-de-piscina', modulo_curso='equipos', orden_curso=10,
             resumen='La bomba mueve el agua a través del sistema. Aprender a reconocer cebado, caudal y señales de falla evita daños y diagnósticos erróneos.',
             funcionamiento='El motor hace girar el impulsor, creando flujo desde la succión hacia el filtro y retornos. La bomba necesita agua para funcionar correctamente y el sistema de succión debe estar razonablemente hermético.', componentes='Motor, cuerpo/voluta, impulsor, prefiltro, canastilla, tapa y O-ring, sello mecánico, conexiones de succión y descarga.', mantenimiento='• Limpia canastilla.\n• Mantén ventilación del motor libre.\n• Revisa fugas.\n• Observa ruidos y vibraciones.\n• Mantén el nivel de agua suficiente para evitar aspiración de aire.', fallas_frecuentes='NO CEBA: revisar nivel de agua, tapa/O-ring, aire en succión, canastilla y obstrucciones.\nRUIDO ANORMAL: puede existir cavitación, residuos o problema mecánico.\nFUGA ENTRE MOTOR Y BOMBA: posible sello mecánico.', buenas_practicas='• Nunca operar en seco.\n• No desmontar partes eléctricas sin capacitación.\n• Desenergizar antes de intervenir.', errores_comunes='• Dejar la bomba trabajando sin agua.\n• Ignorar burbujas persistentes en retornos.\n• Agregar químicos concentrados directamente al prefiltro.', referencias_tecnicas=refs_equipos, etiquetas='bomba,cebado,prefiltro,impulsor,aire'),
        dict(codigo='EQ-002', tipo='equipo', titulo='Filtro de arena', slug='filtro-de-arena', modulo_curso='equipos', orden_curso=20,
             resumen='El filtro de arena retiene partículas mientras el agua atraviesa el medio filtrante. Su presión limpia es una referencia fundamental.',
             funcionamiento='En modo FILTER, el agua atraviesa el lecho filtrante y las partículas quedan retenidas. A medida que se carga de suciedad aumenta la resistencia. El retrolavado invierte el flujo para limpiar el medio.', componentes='Tanque, arena/medio filtrante, difusor, colectores/laterales, manómetro, válvula multipuerto o sistema equivalente.', mantenimiento='• Observa presión de referencia limpia.\n• Realiza retrolavado cuando corresponda según presión/caudal y manual.\n• Inspecciona medio filtrante periódicamente.\n• JVAQUA recomienda cambio de arena como mantenimiento preventivo anual en su estándar comercial, salvo criterio técnico distinto para una instalación concreta.', fallas_frecuentes='PRESIÓN ALTA: filtro cargado, restricción o válvula.\nARENA EN PISCINA: posible lateral/colector dañado o problema de montaje.\nBAJA PRESIÓN/CAUDAL: revisar succión, bomba, nivel de agua y obstrucciones.', buenas_practicas='• Libera presión antes de abrir un filtro.\n• Nunca trabajes sobre un tanque presurizado.\n• Sigue el manual del modelo.', errores_comunes='• Abrir el filtro presurizado.\n• Retrolavar excesivamente sin necesidad.\n• Mover la multiválvula con la bomba encendida.', referencias_tecnicas=refs_equipos, etiquetas='filtro arena,filtracion,manometro,presion'),
        dict(codigo='EQ-003', tipo='equipo', titulo='Multiválvula de seis vías', slug='multivalvula-seis-vias', modulo_curso='equipos', orden_curso=30,
             resumen='La multiválvula dirige el flujo del sistema. Una posición incorrecta puede enviar agua a desagüe o impedir la filtración.',
             funcionamiento='Las posiciones comunes son FILTER, BACKWASH, RINSE, WASTE, RECIRCULATE y CLOSED. La función exacta depende del modelo.', componentes='Palanca/selector, junta interna, puertos de bomba/filtro/retorno/desagüe y cuerpo de válvula.', mantenimiento='Mantén la palanca funcional, revisa fugas y consulta el manual si existe dificultad para cambiar posiciones.', fallas_frecuentes='FUGA A DESAGÜE EN FILTER: posible junta interna dañada o suciedad.\nPALANCA DURA: no la fuerces; revisar según manual.\nFLUJO INCORRECTO: confirmar posición y tuberías.', buenas_practicas='• APAGA la bomba antes de cambiar de posición.\n• Presiona la palanca completamente antes de girarla cuando el diseño así lo requiere.', errores_comunes='• Cambiar de posición con bomba encendida.\n• Dejar CLOSED con la bomba funcionando.\n• Confundir RECIRCULATE con FILTER.', referencias_tecnicas=refs_equipos, etiquetas='multivalvula,filter,backwash,rinse,waste,recirculate'),

        dict(codigo='SG-001', titulo='Seguridad en manejo de químicos', slug='seguridad-quimicos-piscina', modulo_curso='seguridad', orden_curso=10,
             resumen='Reglas esenciales para evitar gases tóxicos, incendios, salpicaduras y reacciones violentas.',
             contenido='Los productos para piscinas pueden reaccionar peligrosamente cuando se mezclan o contaminan. El riesgo aumenta con cloros concentrados, ácidos y recipientes húmedos o contaminados.', procedimiento='• Lee etiqueta y FDS.\n• Trabaja con ventilación adecuada.\n• Usa el EPP indicado.\n• Abre un solo producto a la vez.\n• Mide cuidadosamente.\n• Mantén productos separados.\n• Si la etiqueta indica predisolver, agrega el químico al agua; nunca improvises el orden.', buenas_practicas='• Guarda químicos secos, separados y etiquetados.\n• Usa utensilios dedicados y limpios.\n• Mantén niños/clientes alejados durante manipulación.', errores_comunes='• NUNCA mezclar cloro con ácido: puede producir gases tóxicos.\n• NUNCA mezclar diferentes químicos de piscina en un recipiente.\n• No reutilizar recipientes contaminados.\n• No respirar polvo o vapores deliberadamente.', referencias_tecnicas=refs_seguridad, etiquetas='seguridad,quimicos,cloro,acido,epp'),
        dict(codigo='SG-002', titulo='Seguridad con bombas, filtros y sistemas presurizados', slug='seguridad-equipos-piscina', modulo_curso='seguridad', orden_curso=20,
             resumen='Antes de abrir o intervenir equipos, elimina energía y presión. Los filtros pueden almacenar energía peligrosa por aire comprimido.',
             contenido='Una bomba es un equipo eléctrico y un filtro puede convertirse en un recipiente presurizado. Una intervención incorrecta puede causar lesiones graves.', procedimiento='1. Detén el equipo.\n2. Evita arranque accidental.\n3. Libera presión mediante el procedimiento del fabricante.\n4. Comprueba el manómetro cuando corresponda.\n5. Solo entonces abre tapas o filtros.\n6. Si el trabajo requiere electricidad interna o reparación especializada, escálalo a personal capacitado.', buenas_practicas='• Mantente alejado de tapas/filtros durante arranque hasta confirmar operación normal.\n• Abre válvulas necesarias antes del arranque.', errores_comunes='• Abrir filtros con presión.\n• Trabajar en componentes eléctricos energizados.\n• Arrancar la bomba con líneas cerradas.', referencias_tecnicas='CDC Pool Chemical Safety; manuales oficiales Pentair/Hayward sobre alivio de presión y arranque seguro.', etiquetas='seguridad,bomba,filtro,presion,electricidad'),

        dict(codigo='JV-001', titulo='Estándar de servicio JVAQUA', slug='estandar-servicio-jvaqua', modulo_curso='estandar', orden_curso=10, acceso='interno',
             resumen='Cómo debe comportarse y trabajar un técnico JVAQUA durante una visita.',
             contenido='El estándar combina trabajo técnico, orden, comunicación y registro. El cliente debe percibir profesionalismo antes, durante y después del mantenimiento.', procedimiento='ANTES: revisa agenda, ruta, herramientas e inventario.\nAL LLEGAR: saluda, preséntate y realiza inspección.\nDURANTE: sigue el orden de mantenimiento, cuida el área y registra novedades.\nAL FINAL: deja equipos en condición normal, limpia, toma fotografías, registra datos y comunica novedades importantes.', buenas_practicas='• Trato respetuoso.\n• Uniforme y herramientas ordenadas.\n• No improvisar tratamientos sin medir.\n• Reportar fallas que requieren seguimiento.', errores_comunes='• Llegar y empezar sin inspección.\n• Dejar herramientas/residuos.\n• Omitir información importante al cliente o administración.', recomendaciones_jvaqua='El técnico representa a JVAQUA en cada domicilio. La calidad técnica y la experiencia del cliente forman parte del mismo servicio.', etiquetas='jvaqua,estandar,servicio,cliente,tecnico'),
    ]

    objs = {}
    for item in items:
        objs[item['codigo']] = upsert(**item)

    relaciones = {
        'AC-F-001': ['AC-F-002','EQ-001','EQ-002'],
        'AC-F-003': ['AC-Q-001','AC-Q-002'],
        'AC-Q-001': ['BT-Q-004','BT-Q-007','BT-Q-008'],
        'AC-Q-002': ['BT-Q-001','BT-Q-002','BT-Q-006','AC-Q-004'],
        'AC-Q-004': ['BT-Q-002','AC-Q-002'],
        'PR-M-001': ['AC-F-003','EQ-001','EQ-002'],
        'PR-M-005': ['EQ-001'],
        'PR-M-006': ['EQ-002','EQ-003'],
        'PR-M-008': ['BT-Q-003','BT-Q-001','BT-Q-004'],
        'EQ-001': ['PR-M-005','SG-002'],
        'EQ-002': ['PR-M-006','EQ-003','SG-002'],
        'EQ-003': ['PR-M-006','EQ-002'],
        'SG-001': ['BT-Q-001','BT-Q-002','BT-Q-007'],
        'JV-001': ['PR-M-001','PR-M-009'],
    }
    for code, related_codes in relaciones.items():
        obj = Contenido.objects.filter(codigo=code).first()
        if obj:
            obj.relacionados.add(*Contenido.objects.filter(codigo__in=related_codes))

    consejos = [
        ('Mide antes de dosificar', 'Antes de aplicar un tratamiento, confirma pH y cloro. Una buena dosificación comienza con una buena medición.', 'quimica', 10),
        ('Nunca mezcles cloro y ácido', 'Cloro y ácidos concentrados deben mantenerse separados. Su mezcla puede liberar gases tóxicos.', 'seguridad', 20),
        ('Apaga antes de mover la multiválvula', 'La posición de la multiválvula se cambia siempre con la bomba apagada.', 'filtracion', 30),
        ('No permitas que la bomba trabaje en seco', 'Si la bomba pierde cebado, deténla y corrige la causa antes de continuar.', 'equipos', 40),
        ('Observa antes de intervenir', 'La inspección inicial te dice qué necesita realmente la piscina antes de aspirar o aplicar productos.', 'mantenimiento', 50),
        ('Un retrolavado termina con enjuague', 'Después del BACKWASH, realiza RINSE según el equipo antes de regresar a FILTER.', 'filtracion', 60),
        ('La floculación necesita tiempo', 'En el protocolo JVAQUA, el objetivo preferente es dejar sedimentar alrededor de 24 horas cuando la operación lo permite.', 'quimica', 70),
    ]
    for titulo, texto, categoria, orden in consejos:
        Consejo.objects.update_or_create(titulo=titulo, defaults={'texto':texto,'categoria':categoria,'orden':orden,'activo':True})


def reverse_seed(apps, schema_editor):
    # No borrar conocimiento porque puede haber progreso, favoritos y ediciones posteriores.
    pass


class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0005_academia_aprender_consultar_resolver')]
    operations = [
        migrations.AlterField(
            model_name='contenidoacademia',
            name='modulo_curso',
            field=models.CharField(
                blank=True,
                choices=[
                    ('fundamentos','1. Fundamentos'),('quimica','2. Química del agua'),
                    ('productos','3. Productos químicos'),('mantenimiento','4. Mantenimiento'),
                    ('problemas','5. Problemas del agua'),('equipos','6. Equipos'),
                    ('preventivo','7. Mantenimiento preventivo'),('seguridad','8. Seguridad'),
                    ('estandar','9. Estándar JVAQUA'),('avanzado','10. Conocimiento avanzado'),
                ],
                db_index=True, default='', max_length=30,
            ),
        ),
        migrations.RunPython(seed_curso, reverse_seed),
    ]
