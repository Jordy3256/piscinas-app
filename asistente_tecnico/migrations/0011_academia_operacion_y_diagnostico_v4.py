from django.db import migrations


def seed(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    items = [
        dict(codigo='AC-FUN-007', titulo='Las 4 funciones que mantienen una piscina sana', slug='cuatro-funciones-piscina-sana', tipo='biblioteca', modulo_curso='fundamentos', orden_curso=70, orden=70, nivel='basico', tiempo_lectura_min=7,
             resumen='Circulación, filtración, desinfección y limpieza trabajan juntas. Entender esa relación evita tratar síntomas aislados.',
             introduccion='Una piscina estable no depende de un solo químico. Cuatro funciones deben trabajar juntas: mover el agua, retirar partículas, controlar microorganismos y retirar físicamente la suciedad.',
             contenido='''1. CIRCULACIÓN\nLa bomba mueve el agua para que pueda filtrarse y distribuir el tratamiento.\n\n2. FILTRACIÓN\nEl filtro retiene partículas transportadas por el agua.\n\n3. DESINFECCIÓN\nEl desinfectante ayuda a controlar microorganismos y oxidar contaminantes.\n\n4. LIMPIEZA FÍSICA\nAspirado, cepillado y recolección eliminan residuos que el sistema hidráulico no puede resolver por sí solo.\n\nCuando una de estas cuatro funciones falla, las demás tienen que trabajar más y la calidad del agua suele deteriorarse.''',
             buenas_practicas='• Diagnostica las cuatro funciones antes de aumentar químicos.\n• Mantén circulación y filtración operativas.\n• Combina tratamiento químico con limpieza física.',
             errores_comunes='• Pensar que más cloro compensa un filtro deficiente.\n• Ignorar cepillado y aspirado.\n• Tratar agua sin comprobar circulación.',
             recomendaciones_jvaqua='Ante un problema, pregúntate cuál de las cuatro funciones está fallando antes de decidir la solución.', etiquetas='fundamentos, circulacion, filtracion, desinfeccion, limpieza'),
        dict(codigo='AC-QUI-009', titulo='Por qué el pH cambia y cómo interpretarlo', slug='por-que-cambia-ph-piscina', tipo='biblioteca', modulo_curso='quimica', orden_curso=90, orden=90, nivel='intermedio', tiempo_lectura_min=8,
             resumen='El pH no cambia al azar. Aireación, productos, agua de reposición y equilibrio químico pueden empujarlo hacia arriba o abajo.',
             introduccion='Comprender la tendencia del pH es más útil que corregir el número una sola vez. Una piscina que vuelve repetidamente al mismo problema está dando una pista.',
             contenido='''EL pH PUEDE SUBIR por aireación, características del agua de llenado, ciertos productos y condiciones del equilibrio del agua.\n\nEL pH PUEDE BAJAR por productos ácidos, algunos procesos de tratamiento, lluvia/agua de aporte y otras condiciones químicas.\n\nSi el pH se mueve constantemente, amplía el diagnóstico: revisa alcalinidad, productos utilizados, frecuencia de reposición de agua y operación del sistema.''',
             buenas_practicas='• Observa tendencias, no una lectura aislada.\n• Registra qué producto se aplicó antes del cambio.\n• Repite mediciones dudosas.',
             errores_comunes='• Corregir diariamente sin investigar la causa.\n• Añadir correctores opuestos en poco tiempo.\n• Suponer que todas las piscinas reaccionan igual.',
             recomendaciones_jvaqua='En mantenimiento rutinario medimos pH y CL; cuando existe una tendencia persistente, el diagnóstico debe ampliarse.', etiquetas='ph, tendencia, alcalinidad, balance, diagnostico'),
        dict(codigo='AC-PRO-011', titulo='Alguicida: preventivo no significa sustituto del cloro', slug='alguicida-preventivo-piscina', tipo='biblioteca', modulo_curso='productos', orden_curso=110, orden=110, nivel='basico', tiempo_lectura_min=7,
             resumen='El alguicida puede apoyar la prevención o tratamientos específicos, pero no reemplaza una desinfección y circulación correctas.',
             introduccion='Un error frecuente es utilizar alguicida como solución universal para cualquier agua verde. Primero hay que identificar por qué las algas pudieron desarrollarse.',
             contenido='''FUNCIÓN\nLos alguicidas están formulados para ayudar a prevenir o controlar algas según su composición. La etiqueta define dosis y uso.\n\nANTES DE APLICAR\nComprueba cloro, pH, circulación, filtración y estado real del agua. Una piscina con desinfección insuficiente o mala circulación necesita corregir esas causas.''',
             buenas_practicas='• Utilizar la dosis indicada para el producto.\n• Mantener circulación.\n• Usarlo como complemento cuando corresponda.',
             errores_comunes='• Sustituir cloro por alguicida.\n• Sobredosificar buscando aclarar el agua.\n• Aplicar sin revisar la causa del crecimiento.',
             recomendaciones_jvaqua='En prevención utilizamos dosis ligeras cuando la condición lo justifica; para agua verde el Asistente debe evaluar el tratamiento completo.', etiquetas='alguicida, algas, preventivo, agua verde'),
        dict(codigo='AC-MAN-016', titulo='Cómo cepillar correctamente paredes, piso y esquinas', slug='tecnica-correcta-cepillado-piscina', tipo='procedimiento', modulo_curso='mantenimiento', orden_curso=160, orden=160, nivel='basico', tiempo_lectura_min=7,
             resumen='El cepillado rompe suciedad adherida y biofilm. La técnica y el tipo de cepillo importan tanto como la fuerza.',
             introduccion='Cepillar no es pasar rápidamente el cepillo por la superficie. Debe cubrir zonas donde la circulación y el aspirado suelen ser menos efectivos.',
             procedimiento='''1. Selecciona un cepillo compatible con el acabado.\n2. Comienza por paredes y línea de agua.\n3. Trabaja esquinas, escalones y zonas de baja circulación.\n4. Cepilla hacia el fondo cuando convenga para facilitar la posterior aspiración/filtración.\n5. Insiste de forma controlada donde exista película o inicio de alga.\n6. Revisa visualmente que no queden zonas omitidas.''',
             herramientas_materiales='Cepillo compatible con el acabado, pértiga telescópica y equipo de protección cuando corresponda.',
             buenas_practicas='• Mantener un patrón para cubrir toda la piscina.\n• Prestar atención a esquinas y detrás de accesorios.\n• Cambiar cepillos deteriorados.',
             errores_comunes='• Usar un cepillo agresivo sobre un acabado delicado.\n• Cepillar solo donde se ve suciedad.\n• Omitir línea de agua y escalones.',
             recomendaciones_jvaqua='El cepillado forma parte de la prevención: no esperes a que la pared esté visiblemente verde para hacerlo.', etiquetas='cepillado, paredes, piso, esquinas, biofilm'),
        dict(codigo='AC-PRB-010', titulo='Espuma en la piscina: causas antes de agregar productos', slug='espuma-piscina-causas', tipo='biblioteca', modulo_curso='problemas', orden_curso=100, orden=100, nivel='intermedio', tiempo_lectura_min=7,
             resumen='La espuma puede relacionarse con productos, materia orgánica o contaminación externa. El primer paso es identificar el contexto.',
             introduccion='No toda espuma significa el mismo problema. Antes de aplicar un antiespumante o vaciar agua, revisa qué ocurrió recientemente.',
             contenido='''REVISA\n• Productos añadidos recientemente y sus dosis.\n• Uso excesivo de ciertos alguicidas u otros productos espumantes.\n• Contaminantes introducidos por bañistas.\n• Calidad y renovación del agua.\n• Filtración y limpieza.\n\nLa solución depende de la causa y puede incluir filtración, corrección del tratamiento, renovación parcial de agua u otras medidas específicas.''',
             buenas_practicas='• Preguntar qué se agregó antes de que apareciera.\n• Verificar dosificaciones.\n• Mantener filtración y limpieza.',
             errores_comunes='• Añadir más químicos sin diagnóstico.\n• Confundir espuma con aire proveniente de retornos.\n• Ignorar una sobredosificación reciente.',
             recomendaciones_jvaqua='Documenta la espuma y los productos usados; esa información permite al Asistente orientar mejor el caso.', etiquetas='espuma, alguicida, contaminantes, agua'),
        dict(codigo='AC-EQP-013', titulo='Válvulas de succión y retorno: cómo leer una instalación', slug='valvulas-succion-retorno-piscina', tipo='equipo', modulo_curso='equipos', orden_curso=130, orden=130, nivel='intermedio', tiempo_lectura_min=9,
             resumen='Aprende a identificar qué líneas llevan agua hacia la bomba y cuáles la devuelven a la piscina antes de mover una válvula.',
             introduccion='Mover válvulas sin conocer la instalación puede cortar el caudal, hacer trabajar mal la bomba o enviar agua a una línea equivocada.',
             funcionamiento='''LADO DE SUCCIÓN\nSon líneas que llevan agua desde piscina hacia bomba: por ejemplo skimmer, drenaje o toma de aspiración.\n\nLADO DE RETORNO\nLlevan el agua tratada desde el sistema hacia la piscina u otros circuitos.\n\nLa posición correcta depende del diseño de cada instalación. No existe una configuración universal.''',
             componentes='Válvulas, tuberías de succión, tuberías de retorno, uniones y etiquetas/identificación cuando existan.',
             mantenimiento='Revisar fugas, dureza de accionamiento y estado de uniones. No forzar una válvula bloqueada.',
             fallas_frecuentes='Fugas por sellos, manijas dañadas, válvula parcialmente cerrada, línea mal identificada o entrada de aire en succión.',
             errores_comunes='• Girar varias válvulas a la vez sin registrar posición.\n• Cerrar toda la succión con la bomba operando.\n• Suponer que una tubería tiene la misma función que en otra piscina.',
             recomendaciones_jvaqua='Antes de modificar una instalación desconocida, fotografía la posición inicial. Cambia una cosa por vez y observa el resultado.', etiquetas='valvulas, succion, retorno, tuberias, hidraulica'),
        dict(codigo='AC-PRE-005', titulo='Revisión mensual del cuarto de máquinas', slug='revision-mensual-cuarto-maquinas', tipo='procedimiento', modulo_curso='preventivo', orden_curso=50, orden=50, nivel='intermedio', tiempo_lectura_min=9,
             resumen='Una inspección periódica permite detectar fugas, vibraciones, conexiones deterioradas y restricciones antes de que se conviertan en una avería.',
             introduccion='El cuarto de máquinas debe revisarse como un sistema, no únicamente cuando la bomba deja de funcionar.',
             procedimiento='''1. Observa fugas y humedad.\n2. Escucha ruidos o vibraciones anormales.\n3. Revisa canastilla, tapa y sellos visibles de la bomba.\n4. Comprueba presión y comportamiento del filtro.\n5. Revisa válvulas y uniones.\n6. Comprueba que no existan cables, tableros o componentes eléctricos evidentemente deteriorados.\n7. Mantén ventilación, acceso y orden.\n8. Documenta cualquier anomalía para reparación.''',
             buenas_practicas='• Comparar contra el comportamiento habitual.\n• Mantener el área seca y despejada.\n• Escalar trabajos eléctricos a personal competente.',
             errores_comunes='• Ignorar pequeñas fugas.\n• Almacenar químicos junto a equipos de forma insegura.\n• Manipular electricidad sin competencia.',
             recomendaciones_jvaqua='Una fotografía periódica del cuarto de máquinas ayuda a detectar cambios y facilita diagnósticos posteriores.', etiquetas='preventivo, cuarto maquinas, bomba, filtro, fugas'),
        dict(codigo='AC-SEG-005', titulo='Qué hacer ante un derrame químico', slug='derrame-quimico-piscina-seguridad', tipo='procedimiento', modulo_curso='seguridad', orden_curso=50, orden=50, nivel='intermedio', tiempo_lectura_min=8,
             resumen='Ante un derrame, la prioridad es proteger personas y evitar mezclas peligrosas. No improvises una neutralización.',
             introduccion='Los procedimientos exactos dependen del producto. La etiqueta y la hoja de datos de seguridad (SDS) son la referencia principal.',
             procedimiento='''1. Mantén alejadas a personas no necesarias.\n2. Identifica el producto sin tocarlo directamente.\n3. Evita que entre en contacto con otros químicos o materiales incompatibles.\n4. Utiliza el EPP indicado por etiqueta/SDS.\n5. Sigue el procedimiento de contención y limpieza especificado para ese producto.\n6. Si existe reacción, humo, calor, incendio, exposición importante o no puedes controlar el evento con seguridad, aléjate y solicita ayuda de emergencia/profesional.''',
             buenas_practicas='• Tener SDS accesibles.\n• Mantener productos identificados.\n• Disponer de EPP apropiado.\n• Capacitar antes de una emergencia.',
             errores_comunes='• Mezclar otro químico para “neutralizar”.\n• Barrer productos incompatibles juntos.\n• Devolver material contaminado al envase.',
             recomendaciones_jvaqua='La seguridad tiene prioridad sobre recuperar producto o continuar el mantenimiento. Si no conoces el procedimiento específico, detén la intervención.', referencias_tecnicas='CDC — Pool Chemical Safety; etiqueta y SDS del fabricante del producto.', etiquetas='derrame, seguridad, quimicos, SDS, emergencia'),
        dict(codigo='AC-ADV-003', titulo='Diagnóstico combinado: agua turbia con presión alta', slug='diagnostico-agua-turbia-presion-alta', tipo='procedimiento', modulo_curso='avanzado', orden_curso=30, orden=30, nivel='avanzado', tiempo_lectura_min=9,
             resumen='Aprende a integrar dos síntomas en vez de tratarlos por separado: mala claridad y aumento de presión del filtro.',
             introduccion='Cuando aparecen varios síntomas a la vez, busca una causa que pueda explicarlos conjuntamente. La presión alta respecto a la referencia puede indicar resistencia en filtración mientras la turbidez señala partículas que no están siendo retiradas adecuadamente.',
             procedimiento='''1. Confirma que la presión realmente está por encima de la referencia limpia.\n2. Revisa caudal de retornos.\n3. Inspecciona condición del filtro y realiza el mantenimiento correspondiente si está cargado.\n4. Verifica pH y CL.\n5. Evalúa carga de partículas, uso reciente y tratamiento aplicado.\n6. Restablece filtración adecuada antes de decidir tratamientos adicionales.\n7. Revisa nuevamente claridad y presión después del tiempo de operación necesario.''',
             buenas_practicas='• Relacionar presión, caudal y claridad.\n• Corregir problemas mecánicos antes de sobretratar químicamente.\n• Registrar presión antes/después.',
             errores_comunes='• Añadir floculante sin comprobar el filtro.\n• Retrolavar repetidamente sin investigar.\n• Tratar cada síntoma como un problema independiente.',
             recomendaciones_jvaqua='Entrega al Asistente pH, CL, presión habitual/actual, tipo de filtro y fotografías para obtener una orientación más precisa.', etiquetas='diagnostico, agua turbia, presion alta, filtro, avanzado'),
    ]
    for item in items:
        data = dict(item)
        data.update(estado='aprobado', version='1.0', acceso='compartido')
        Contenido.objects.update_or_create(codigo=data['codigo'], defaults=data)


def reverse(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    Contenido.objects.filter(codigo__in=['AC-FUN-007','AC-QUI-009','AC-PRO-011','AC-MAN-016','AC-PRB-010','AC-EQP-013','AC-PRE-005','AC-SEG-005','AC-ADV-003']).delete()


class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0010_academia_formacion_esencial_v3')]
    operations = [migrations.RunPython(seed, reverse)]
