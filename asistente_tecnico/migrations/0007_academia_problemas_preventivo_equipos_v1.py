from django.db import migrations


def seed_contenido(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    Consejo = apps.get_model('asistente_tecnico', 'ConsejoJVAQUA')

    def upsert(codigo, **data):
        defaults = {
            'tipo': data.pop('tipo', 'biblioteca'),
            'titulo': data.pop('titulo'),
            'slug': data.pop('slug'),
            'resumen': data.pop('resumen', ''),
            'nivel': data.pop('nivel', 'basico'),
            'tiempo_lectura_min': data.pop('tiempo_lectura_min', 6),
            'estado': 'aprobado',
            'version': '1.0',
            'acceso': data.pop('acceso', 'compartido'),
            'modulo_curso': data.pop('modulo_curso', ''),
            'orden_curso': data.pop('orden_curso', 0),
            'orden': data.pop('orden', 0),
        }
        defaults.update(data)
        obj, _ = Contenido.objects.update_or_create(codigo=codigo, defaults=defaults)
        return obj

    items = [
        dict(codigo='PB-001', titulo='Agua verde: diagnóstico y recuperación', slug='agua-verde-diagnostico-recuperacion', modulo_curso='problemas', orden_curso=10,
             resumen='Cómo identificar por qué una piscina se vuelve verde y organizar una recuperación sin aplicar productos a ciegas.',
             contenido='El agua verde suele estar asociada a crecimiento de algas y a una desinfección insuficiente, pero el color por sí solo no sustituye la medición. Antes de tratar, revisa pH, cloro, circulación, filtración, carga de suciedad y estado general del sistema.',
             procedimiento='1. Inspecciona el agua y el sistema.\n2. Mide pH y cloro.\n3. Corrige primero las condiciones que impidan una desinfección eficaz.\n4. Cepilla paredes, piso, esquinas y zonas de baja circulación.\n5. Aplica el tratamiento de recuperación definido para el volumen y condición real.\n6. Mantén filtración/circulación según el procedimiento.\n7. Retira material sedimentado o retenido por el filtro.\n8. Vuelve a medir antes de dar el caso por resuelto.',
             buenas_practicas='• Diagnostica antes de dosificar.\n• Cepilla para desprender biopelícula y algas adheridas.\n• Revisa que la filtración realmente esté funcionando.\n• Documenta la evolución del agua.',
             errores_comunes='• Aplicar alguicida o cloro sin medir.\n• Ignorar un filtro saturado.\n• Dar por terminada la recuperación solo porque cambió el color.\n• Mezclar productos entre sí.',
             recomendaciones_jvaqua='En JVAQUA el tratamiento de choque se reserva para condiciones que lo justifican, como turbidez importante, agua verde o cloro muy bajo; el tratamiento debe ajustarse a la medición y al estado real.', etiquetas='agua verde,algas,recuperacion,shock,cloro,pH'),
        dict(codigo='PB-002', titulo='Agua turbia: causas y corrección', slug='agua-turbia-causas-correccion', modulo_curso='problemas', orden_curso=20,
             resumen='La turbidez puede venir de química, partículas, filtración deficiente o una combinación de varias causas.',
             contenido='El agua turbia no tiene una única solución. Puede aparecer por partículas suspendidas, filtración insuficiente, suciedad, desequilibrios químicos o después de un tratamiento. El diagnóstico debe separar la causa antes de elegir clarificación, floculación o corrección del sistema.',
             procedimiento='1. Mide pH y cloro.\n2. Comprueba caudal, presión y estado del filtro.\n3. Revisa si existe suciedad fina en suspensión o sedimentada.\n4. Corrige primero parámetros y filtración.\n5. Si corresponde, usa clarificante para partículas finas o floculación cuando se necesita sedimentación y aspirado a desagüe.\n6. Revisa el resultado antes de repetir productos.',
             buenas_practicas='• Diferencia agua ligeramente opaca de turbidez severa.\n• Limpia/retrolava el filtro cuando corresponda.\n• Respeta el tiempo de sedimentación cuando se flocula.',
             errores_comunes='• Añadir más y más productos sin esperar resultados.\n• Flocular sin posibilidad de aspirar correctamente el sedimento.\n• Aspirar sedimento fino hacia el filtro cuando el procedimiento requiere desagüe.', etiquetas='agua turbia,turbidez,clarificante,floculante,filtro'),
        dict(codigo='PB-003', titulo='Cloro bajo o ausente', slug='cloro-bajo-ausente', modulo_curso='problemas', orden_curso=30,
             resumen='Qué revisar cuando la medición muestra poco o ningún cloro disponible.',
             contenido='Un cloro bajo puede deberse a demanda elevada, dosificación insuficiente, radiación solar, contaminación, problemas de circulación o condiciones del agua que reducen la eficacia del tratamiento.',
             procedimiento='1. Confirma la medición con un método en buen estado.\n2. Revisa pH.\n3. Observa claridad, algas y carga de bañistas/suciedad.\n4. Comprueba circulación y dosificación.\n5. Aplica la corrección correspondiente al volumen y vuelve a medir después del tiempo adecuado.',
             buenas_practicas='• No confundas “agregué cloro” con “tengo cloro residual medible”.\n• Registra el valor antes y después cuando sea posible.',
             errores_comunes='• Repetir dosis sin volver a medir.\n• Ignorar un pH fuera de rango.\n• Usar una lectura dudosa como base para una dosis grande.', etiquetas='cloro bajo,cloro libre,desinfeccion,medicion'),
        dict(codigo='PB-004', titulo='pH alto y pH bajo: cómo interpretar el problema', slug='ph-alto-bajo-interpretacion', modulo_curso='problemas', orden_curso=40,
             resumen='El pH modifica la comodidad, la protección de equipos y la eficacia del tratamiento; se corrige de forma gradual y con medición.',
             contenido='JVAQUA utiliza como referencia operativa pH 7,2–7,6. Un valor fuera de ese rango requiere analizar la causa y corregir gradualmente. No debe tratarse como una cifra aislada: revisa también desinfectante, productos aplicados y comportamiento histórico de la piscina.',
             procedimiento='1. Confirma la lectura.\n2. Identifica si debe subir o bajar.\n3. Calcula una corrección prudente según producto, concentración y volumen.\n4. Distribuye según etiqueta/procedimiento.\n5. Permite circulación.\n6. Vuelve a medir antes de repetir.',
             buenas_practicas='• Realiza correcciones progresivas.\n• Usa siempre la concentración real del producto disponible.',
             errores_comunes='• Intentar corregir todo en una sola aplicación.\n• Aplicar elevador y reductor juntos.\n• Dosificar sin conocer el volumen.', recomendaciones_jvaqua='Cuando se usa metasilicato para elevar pH, JVAQUA prefiere corrección gradual y una nueva medición aproximadamente 10 minutos después, siempre que exista buena circulación y el producto/protocolo utilizado lo permita.', etiquetas='pH alto,pH bajo,metasilicato,reductor pH'),
        dict(codigo='PB-005', titulo='Arena o suciedad regresa a la piscina', slug='arena-suciedad-regresa-piscina', modulo_curso='problemas', orden_curso=50,
             resumen='Cómo diferenciar suciedad que vuelve por los retornos de una posible falla interna del filtro.',
             contenido='Si después de aspirar o filtrar aparecen partículas por los retornos, primero determina si realmente es arena del filtro o suciedad fina que atravesó el sistema. Una pérdida continua de medio filtrante puede indicar un problema interno que requiere revisión.',
             procedimiento='1. Observa el tipo de partícula.\n2. Revisa presión y funcionamiento del filtro.\n3. Confirma posición de multiválvula.\n4. Realiza retrolavado/enjuague cuando corresponda.\n5. Si aparece medio filtrante de forma persistente, detén el diagnóstico superficial y programa revisión interna del filtro.',
             buenas_practicas='• No abras un filtro presurizado.\n• Documenta dónde aparecen las partículas.',
             errores_comunes='• Cambiar arena sin diagnosticar laterales/colector.\n• Confundir polvo fino con arena del filtro.', etiquetas='arena piscina,retornos,filtro,laterales,suciedad'),
        dict(codigo='PB-006', titulo='Bomba con poco caudal o pérdida de cebado', slug='bomba-poco-caudal-perdida-cebado', modulo_curso='problemas', orden_curso=60,
             resumen='Secuencia básica para revisar una bomba que mueve poca agua, toma aire o pierde cebado.',
             contenido='El bajo caudal puede originarse antes de la bomba, dentro de la bomba, en el filtro o después del filtro. El diagnóstico ordenado evita desmontar equipos innecesariamente.',
             procedimiento='1. Revisa nivel de agua.\n2. Revisa canastillas y posibles obstrucciones.\n3. Observa si entra aire por la tapa o succión.\n4. Comprueba válvulas y posición de multiválvula.\n5. Revisa presión del filtro.\n6. Si el problema continúa, escala a diagnóstico técnico de impulsor, tuberías o componentes.',
             buenas_practicas='• Nunca dejes la bomba trabajando en seco.\n• Apaga y libera presión antes de intervenir componentes.',
             errores_comunes='• Culpar inmediatamente al motor.\n• Operar durante mucho tiempo sin cebado.\n• Abrir el sistema con presión.', etiquetas='bomba,cebado,caudal,aire,succion'),

        dict(codigo='PV-001', tipo='procedimiento', titulo='Cambio preventivo de arena del filtro', slug='cambio-preventivo-arena-filtro', modulo_curso='preventivo', orden_curso=10, nivel='intermedio', tiempo_lectura_min=8,
             resumen='Procedimiento general y estándar JVAQUA para renovar el medio filtrante de un filtro de arena.',
             contenido='El medio filtrante pierde desempeño por suciedad acumulada, compactación, canalización o deterioro. JVAQUA recomienda comercialmente realizar el cambio de arena una vez al año como mantenimiento preventivo, sin perjuicio de revisar antes si el equipo o fabricante exige otro criterio.',
             herramientas_materiales='EPP, herramienta adecuada al filtro, recipiente/aspiración para retirar arena, medio filtrante de granulometría y cantidad compatibles con el fabricante, lubricante compatible cuando corresponda.',
             procedimiento='1. Apaga y aísla el sistema.\n2. Libera completamente la presión.\n3. Abre el filtro según su manual.\n4. Retira el medio filtrante evitando dañar laterales/colector.\n5. Inspecciona componentes internos.\n6. Limpia el tanque.\n7. Protege la tubería central cuando corresponda y carga el medio correcto.\n8. Cierra correctamente.\n9. Realiza puesta en marcha, retrolavado y enjuague según el fabricante.\n10. Comprueba fugas y presión normal.',
             buenas_practicas='• Confirma cantidad y granulometría antes de comenzar.\n• Aprovecha para inspeccionar laterales y juntas.', errores_comunes='• Abrir con presión.\n• Usar arena inadecuada.\n• Dañar laterales al retirar el medio.\n• Volver directamente a FILTER sin acondicionar el medio según procedimiento.', recomendaciones_jvaqua='Recomendación preventiva JVAQUA: cambio anual de arena.', etiquetas='cambio arena,filtro,mantenimiento preventivo'),
        dict(codigo='PV-002', tipo='procedimiento', titulo='Mantenimiento preventivo de bomba', slug='mantenimiento-preventivo-bomba', modulo_curso='preventivo', orden_curso=20, nivel='intermedio',
             resumen='Inspecciones que ayudan a detectar problemas de bomba antes de que provoquen una parada.',
             contenido='El mantenimiento preventivo busca detectar fugas, ruido, calentamiento, obstrucciones y problemas de cebado antes de que se conviertan en una avería.',
             procedimiento='• Revisa canastilla y tapa.\n• Observa fugas.\n• Escucha ruidos anormales.\n• Comprueba cebado y caudal.\n• Revisa ventilación exterior del motor sin intervenir componentes energizados.\n• Mantén el área seca y despejada.\n• Escala trabajos eléctricos o mecánicos internos a personal capacitado.',
             buenas_practicas='Registra cambios de ruido, vibración o caudal; suelen ser señales tempranas.', errores_comunes='• Esperar a que la bomba deje de funcionar para revisarla.\n• Manipular conexiones eléctricas energizadas.', etiquetas='bomba,mantenimiento preventivo,canastilla,ruido,fuga'),
        dict(codigo='PV-003', tipo='procedimiento', titulo='Revisión preventiva de filtración y presión', slug='revision-preventiva-filtracion-presion', modulo_curso='preventivo', orden_curso=30,
             resumen='Usar caudal, manómetro y estado del agua como señales para anticipar problemas de filtración.',
             contenido='La presión debe interpretarse respecto de la condición normal del propio sistema. Una lectura aislada no explica por sí sola el problema.',
             procedimiento='1. Observa el manómetro con sistema estable.\n2. Compara con la presión limpia habitual si se conoce.\n3. Revisa caudal en retornos.\n4. Inspecciona filtro, válvulas y canastillas.\n5. Retrolava/limpia cuando corresponda.\n6. Investiga lecturas persistentemente anormales.',
             buenas_practicas='Aprende la presión normal de cada instalación.', errores_comunes='• Usar un único valor universal de presión para todas las piscinas.\n• Ignorar un manómetro averiado.', etiquetas='presion,manometro,filtro,caudal,preventivo'),
        dict(codigo='PV-004', tipo='procedimiento', titulo='Inspección preventiva hidráulica', slug='inspeccion-preventiva-hidraulica', modulo_curso='preventivo', orden_curso=40, nivel='intermedio',
             resumen='Revisión visual y funcional de tuberías, válvulas, uniones, retornos, skimmer y drenajes accesibles.',
             contenido='Muchas pérdidas de rendimiento comienzan como pequeñas fugas, entradas de aire, válvulas parcialmente cerradas u obstrucciones.',
             procedimiento='• Busca fugas visibles.\n• Revisa uniones y válvulas accesibles.\n• Observa aire en la bomba.\n• Comprueba flujo de retornos.\n• Revisa skimmer y nivel de agua.\n• Reporta pérdidas de nivel o síntomas que requieran prueba especializada.',
             buenas_practicas='Fotografía y reporta cambios antes de desmontar componentes.', errores_comunes='• Apretar conexiones indiscriminadamente.\n• Confundir evaporación con fuga sin evaluar el contexto.', etiquetas='hidraulica,fugas,valvulas,retornos,skimmer'),

        dict(codigo='EQ-004', tipo='equipo', titulo='Skimmer', slug='skimmer-piscina', modulo_curso='equipos', orden_curso=40,
             resumen='El skimmer recoge agua superficial y residuos flotantes antes de que lleguen al fondo.',
             funcionamiento='La succión atrae agua superficial hacia una canastilla que retiene hojas y residuos grandes antes de la bomba.', componentes='Boca, compuerta/flotador según modelo, canastilla, tapa y conexión de succión.', mantenimiento='Vacía la canastilla, revisa obstrucciones y comprueba que el nivel de agua permita trabajar correctamente.', fallas_frecuentes='Poca succión: canastilla llena, nivel incorrecto, válvula o línea restringida. Entrada de aire: nivel bajo o vórtice.', errores_comunes='Operar con nivel demasiado bajo o dejar la canastilla saturada.', etiquetas='skimmer,succion,canastilla,nivel agua'),
        dict(codigo='EQ-005', tipo='equipo', titulo='Retornos y boquillas de impulsión', slug='retornos-boquillas-impulsion', modulo_curso='equipos', orden_curso=50,
             resumen='Los retornos devuelven el agua filtrada y ayudan a distribuir tratamiento y movimiento por toda la piscina.',
             funcionamiento='Reciben el agua desde el sistema de filtración y la impulsan de vuelta al vaso. Su orientación influye en la circulación.', componentes='Boquilla, cuerpo, conexión hidráulica y accesorios según instalación.', mantenimiento='Comprueba flujo y orientación; reporta retornos sin caudal o con diferencias marcadas.', fallas_frecuentes='Caudal bajo por obstrucción, válvulas, filtro o bomba. Burbujas persistentes pueden indicar aire en el circuito.', errores_comunes='Orientar todos los retornos sin considerar la circulación del vaso.', etiquetas='retornos,boquillas,circulacion,impulsion'),
        dict(codigo='EQ-006', tipo='equipo', titulo='Drenaje de fondo', slug='drenaje-fondo-piscina', modulo_curso='equipos', orden_curso=60,
             resumen='Punto de captación inferior que forma parte de la circulación hidráulica en muchas piscinas.',
             funcionamiento='Según el diseño, contribuye a captar agua desde zonas profundas y se integra con otras líneas de succión.', componentes='Rejilla/cubierta, cuerpo y tubería de succión según instalación.', mantenimiento='Inspección visual de la cubierta y funcionamiento general. Cualquier intervención sobre succión sumergida debe respetar normas de seguridad y diseño.', fallas_frecuentes='Obstrucción, bajo flujo o daños visibles en cubierta requieren evaluación.', errores_comunes='Manipular cubiertas o sistemas de succión sin criterio técnico.', etiquetas='drenaje fondo,succion,circulacion,seguridad'),
        dict(codigo='EQ-007', tipo='equipo', titulo='Bomba de calor para piscina', slug='bomba-calor-piscina', modulo_curso='equipos', orden_curso=70, nivel='intermedio',
             resumen='Equipo que transfiere calor del ambiente al agua y necesita caudal, ventilación y condiciones eléctricas correctas.',
             funcionamiento='La bomba de calor utiliza un circuito frigorífico para transferir energía al agua que circula por su intercambiador.', componentes='Compresor, evaporador, ventilador, intercambiador, sensores, control y conexiones hidráulicas/eléctricas.', mantenimiento='Mantén libre el flujo de aire, revisa suciedad exterior, caudal de agua, mensajes de error y condiciones indicadas por el fabricante. Reparaciones frigoríficas o eléctricas corresponden a personal capacitado.', fallas_frecuentes='No calienta: revisar demanda, configuración, caudal, temperatura ambiente y códigos de error. Ciclos anormales requieren diagnóstico.', errores_comunes='Bloquear ventilación, operar sin caudal adecuado o intervenir el circuito frigorífico sin capacitación.', etiquetas='bomba calor,calefaccion,temperatura,caudal'),
        dict(codigo='EQ-008', tipo='equipo', titulo='Dosificador de tricloro', slug='dosificador-tricloro', modulo_curso='equipos', orden_curso=80, nivel='intermedio',
             resumen='Dispositivo que permite disolver tabletas de tricloro de forma controlada dentro del circuito diseñado para ello.',
             funcionamiento='El agua atraviesa o contacta las tabletas y transporta el desinfectante disuelto al sistema. El diseño y ajuste dependen del modelo.', componentes='Cuerpo, tapa, regulación, conexiones y elementos internos según fabricante.', mantenimiento='Trabaja con el sistema apagado y sin presión antes de abrir cuando así lo indique el fabricante; revisa juntas y nunca mezcles productos incompatibles dentro del dosificador.', fallas_frecuentes='Dosificación baja por flujo insuficiente, obstrucción o ajuste; fugas por tapa/junta.', errores_comunes='Introducir productos distintos a los permitidos, mezclar cloros o abrir un equipo presurizado.', etiquetas='dosificador,tricloro,pastillas,cloro'),
    ]

    objs = {}
    for item in items:
        code = item.pop('codigo')
        objs[code] = upsert(code, **item)

    relations = {
        'PB-001': ['AC-Q-001','AC-Q-002','BT-Q-001','BT-Q-005','PR-M-003'],
        'PB-002': ['AC-Q-001','AC-Q-002','BT-Q-003','BT-Q-006','PR-M-008'],
        'PB-003': ['AC-Q-002','BT-Q-001','BT-Q-002'],
        'PB-004': ['AC-Q-001','BT-Q-004','BT-Q-007','BT-Q-008'],
        'PB-005': ['EQ-002','EQ-003','PR-M-006'],
        'PB-006': ['EQ-001','PR-M-005','SG-002'],
        'PV-001': ['EQ-002','EQ-003','PR-M-006','SG-002'],
        'PV-002': ['EQ-001','SG-002'],
        'PV-003': ['EQ-002','PR-M-006'],
        'PV-004': ['EQ-004','EQ-005','EQ-006'],
        'EQ-004': ['AC-F-002','PV-004'],
        'EQ-005': ['AC-F-002','PV-004'],
        'EQ-006': ['AC-F-002','PV-004','SG-002'],
        'EQ-007': ['SG-002'],
        'EQ-008': ['BT-Q-002','SG-001'],
    }
    for code, related_codes in relations.items():
        obj = Contenido.objects.filter(codigo=code).first()
        if obj:
            obj.relacionados.add(*Contenido.objects.filter(codigo__in=related_codes))

    consejos = [
        ('El agua verde se diagnostica antes de tratar', 'Mide pH y cloro y confirma circulación/filtración antes de decidir el tratamiento.', 'problemas', 80),
        ('La presión útil es la presión normal de esa piscina', 'Compara el manómetro con la condición limpia habitual del propio sistema, no con un número universal.', 'filtracion', 90),
        ('Un problema de caudal se revisa en orden', 'Nivel de agua, canastillas, aire, válvulas, filtro y luego componentes internos.', 'equipos', 100),
    ]
    for titulo, texto, categoria, orden in consejos:
        Consejo.objects.update_or_create(titulo=titulo, defaults={'texto': texto, 'categoria': categoria, 'orden': orden, 'activo': True})


def reverse_seed(apps, schema_editor):
    # No se elimina contenido para preservar progreso, favoritos y ediciones del CMS.
    pass


class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0006_academia_curso_base_v1')]
    operations = [migrations.RunPython(seed_contenido, reverse_seed)]
