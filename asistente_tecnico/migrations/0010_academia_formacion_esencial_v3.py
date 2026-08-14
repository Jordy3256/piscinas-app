from django.db import migrations


def seed(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    items = [
        dict(codigo='AC-FUN-006', titulo='El recorrido del agua: entiende tu piscina en 5 minutos', slug='recorrido-agua-piscina', tipo='biblioteca', modulo_curso='fundamentos', orden_curso=60, orden=60, nivel='basico', tiempo_lectura_min=6,
             resumen='Visualiza el recorrido desde skimmer y drenaje hasta bomba, filtro y retornos para comprender casi cualquier problema de circulación.',
             introduccion='''Antes de aprender productos o diagnósticos conviene entender por dónde viaja el agua. Ese recorrido conecta prácticamente todos los equipos de la piscina.\n\nRUTA BÁSICA\nPiscina → skimmer/drenaje → bomba → filtro → tratamiento/equipos → retornos → piscina.''',
             contenido='''SUCCIÓN\nEl agua sale de la piscina por skimmers, drenajes u otras tomas. Las válvulas determinan qué líneas están abiertas.\n\nBOMBA\nLa bomba crea el movimiento. Su canastilla retiene residuos grandes antes del impulsor.\n\nFILTRO\nRetiene partículas que el agua transporta. Si está saturado o el medio filtrante está deteriorado, la calidad de filtración cae.\n\nRETORNO\nEl agua vuelve por las boquillas de retorno. Un retorno débil puede ser señal de restricción, aire, filtro sucio, válvula mal posicionada o problema de bomba.''',
             buenas_practicas='''• Aprende a identificar físicamente cada línea.\n• Observa fuerza y dirección de los retornos.\n• Revisa el recorrido completo antes de culpar a un solo equipo.''',
             errores_comunes='''• Pensar que el filtro “succiona” por sí solo.\n• Cerrar líneas sin conocer su función.\n• Diagnosticar únicamente mirando el agua.''',
             recomendaciones_jvaqua='''Cuando una piscina tenga poca circulación, sigue mentalmente el agua desde la toma hasta el retorno. Revisar por etapas hace el diagnóstico mucho más rápido.''', etiquetas='recorrido agua, circulacion, skimmer, drenaje, bomba, filtro, retorno'),
        dict(codigo='AC-QUI-008', titulo='Cómo medir pH y cloro correctamente', slug='medir-ph-cloro-correctamente', tipo='procedimiento', modulo_curso='quimica', orden_curso=80, orden=80, nivel='basico', tiempo_lectura_min=7,
             resumen='Una recomendación solo puede ser tan buena como la medición. Aprende a tomar una muestra representativa y evitar lecturas engañosas.',
             introduccion='''pH y cloro son los dos parámetros operativos que JVAQUA utiliza como referencia principal durante el mantenimiento rutinario. Una muestra mal tomada puede llevar a corregir algo que realmente estaba bien.''',
             procedimiento='''1. Usa un kit limpio y reactivos vigentes.\n2. Toma agua representativa, evitando medir justo donde acaba de caer un químico.\n3. Enjuaga el recipiente de prueba con agua de la piscina.\n4. Llena hasta la marca indicada.\n5. Añade el reactivo exactamente como indique el kit.\n6. Mezcla según el método del fabricante.\n7. Compara el resultado con buena iluminación.\n8. Registra pH y CL antes de decidir una corrección.''',
             buenas_practicas='''• Mantener reactivos cerrados, limpios y protegidos del calor.\n• Repetir una lectura que parezca incoherente.\n• Medir antes y, cuando corresponda, después del tratamiento.''',
             errores_comunes='''• Contaminar tapas o goteros.\n• Usar más reactivo “para que se vea mejor”.\n• Medir inmediatamente encima de una pastilla o punto de dosificación.\n• Adivinar el valor entre colores sin buena luz.''',
             recomendaciones_jvaqua='''Si la lectura no concuerda con el estado de la piscina, repite la medición antes de dosificar. El Asistente Técnico debe recibir datos confiables.''', etiquetas='medir ph, medir cloro, test kit, reactivos, muestra'),
        dict(codigo='AC-SEG-004', titulo='Almacenamiento y manipulación segura de químicos', slug='almacenamiento-seguro-quimicos-piscina', tipo='biblioteca', modulo_curso='seguridad', orden_curso=40, orden=40, nivel='basico', tiempo_lectura_min=8,
             resumen='Aprende a separar, proteger y manipular productos de piscina para reducir riesgos de reacciones, derrames y exposición.',
             introduccion='''Los químicos para piscina pueden reaccionar peligrosamente si se mezclan entre sí, se contaminan o se almacenan de forma incorrecta. La seguridad comienza antes de abrir el envase.''',
             contenido='''REGLAS CLAVE\n• Conserva cada producto en su envase original y correctamente identificado.\n• Mantén los productos secos, ventilados y protegidos de calor y humedad.\n• Separa productos incompatibles.\n• Utiliza herramientas limpias y exclusivas cuando corresponda.\n• Nunca devuelvas producto derramado o contaminado al envase original.\n• Sigue la etiqueta y la hoja de seguridad del fabricante.''',
             buenas_practicas='''• Usar protección personal apropiada.\n• Abrir envases con cuidado y lejos del rostro.\n• Transportar recipientes cerrados y estables.\n• Mantener químicos fuera del alcance de niños y personas no autorizadas.''',
             errores_comunes='''• Mezclar productos concentrados entre sí.\n• Guardar químicos húmedos o sin tapa.\n• Reutilizar cucharas contaminadas entre productos.\n• Trasvasar químicos a botellas de bebidas.''',
             recomendaciones_jvaqua='''Si existe duda sobre compatibilidad o seguridad, no improvises. Consulta la etiqueta/SDS y escala el caso antes de manipular el producto.''',
             referencias_tecnicas='CDC — Pool Chemical Safety; EPA — prácticas de seguridad y etiquetado de productos químicos.', etiquetas='seguridad, almacenamiento, quimicos, incompatibles, EPP, SDS'),
        dict(codigo='AC-MAN-015', titulo='Rutina completa de un mantenimiento semanal', slug='rutina-mantenimiento-semanal-piscina', tipo='procedimiento', modulo_curso='mantenimiento', orden_curso=150, orden=150, nivel='basico', tiempo_lectura_min=10,
             resumen='Una guía de principio a fin para no olvidar ninguna revisión importante durante una visita rutinaria.',
             introduccion='''Una buena rutina evita trabajar por memoria o saltarse pasos. El orden puede adaptarse a cada instalación, pero la inspección, limpieza, circulación y control químico deben quedar cubiertos.''',
             procedimiento='''1. INSPECCIÓN: estado del agua, nivel, bomba, filtro y entorno.\n2. MEDICIÓN: registra pH y CL antes de decidir productos.\n3. ASPIRADO: retira sedimentos del fondo según necesidad.\n4. CEPILLADO: paredes, piso, esquinas y zonas con tendencia a biofilm/algas.\n5. RECOLECCIÓN: hojas y residuos superficiales.\n6. CANASTILLAS/FILTROS: limpia lo necesario y verifica circulación.\n7. RETROLAVADO: solo cuando el filtro/condición lo justifique.\n8. TRATAMIENTO: ajusta según mediciones y condición real.\n9. REVISIÓN FINAL: confirma circulación, orden del área y estado general.\n10. REGISTRO: documenta el trabajo y cualquier novedad.''',
             buenas_practicas='''• Mantener una secuencia consistente.\n• Resolver primero problemas de circulación que impidan tratar bien el agua.\n• Informar fallas que requieren reparación.''',
             errores_comunes='''• Aplicar químicos antes de medir.\n• Hacer retrolavado por costumbre aunque no sea necesario.\n• Terminar sin comprobar que la bomba quedó operando correctamente.''',
             recomendaciones_jvaqua='''La aplicación de mantenimiento del trabajador ya funciona como checklist operativo. Usa esta lección como referencia para entender el propósito de cada paso.''', etiquetas='rutina semanal, mantenimiento, checklist, limpieza, inspeccion'),
        dict(codigo='AC-EQP-012', titulo='Manómetro del filtro: qué te está diciendo', slug='manometro-filtro-presion', tipo='equipo', modulo_curso='equipos', orden_curso=120, orden=120, nivel='basico', tiempo_lectura_min=7,
             resumen='La presión del filtro es una pista de diagnóstico. Aprende a compararla con la presión normal de esa instalación, no con un número universal.',
             introduccion='''El manómetro mide presión en el sistema de filtración. Su valor cobra sentido cuando conoces la presión limpia/normal de esa piscina.''',
             funcionamiento='''PRESIÓN MAYOR A LA HABITUAL\nPuede indicar filtro cargado, restricción en retorno u otra resistencia aguas abajo de la bomba.\n\nPRESIÓN MENOR A LA HABITUAL\nPuede aparecer cuando falta caudal por canastilla obstruida, nivel bajo, entrada de aire, válvula restringida o problema de bomba.\n\nPRESIÓN CERO\nPuede significar bomba apagada/sin caudal, manómetro averiado u otra condición que debe verificarse.''',
             buenas_practicas='''• Conocer la presión de referencia con el filtro limpio.\n• Observar presión junto con caudal de retornos.\n• Cambiar un manómetro claramente averiado antes de usarlo para diagnosticar.''',
             errores_comunes='''• Pensar que existe una presión “perfecta” igual para todas las piscinas.\n• Retrolavar solo porque un número parece alto sin conocer la referencia.\n• Ignorar un manómetro trabado.''',
             recomendaciones_jvaqua='''Compara contra el comportamiento histórico de esa instalación. Presión y caudal deben analizarse juntos.''', etiquetas='manometro, presion, filtro, retrolavado, caudal'),
        dict(codigo='AC-PRO-009', titulo='Hipoclorito de calcio: uso y precauciones', slug='hipoclorito-calcio-piscina', tipo='biblioteca', modulo_curso='productos', orden_curso=90, orden=90, nivel='intermedio', tiempo_lectura_min=8,
             resumen='Desinfectante granular concentrado utilizado en muchas piscinas; conoce su función, sus límites y por qué nunca debe mezclarse con otros cloros concentrados.',
             introduccion='''El hipoclorito de calcio es una fuente sólida de cloro. Su concentración y recomendaciones cambian según el producto comercial, por lo que la etiqueta del fabricante siempre prevalece.''',
             contenido='''FUNCIÓN\nAporta cloro disponible para desinfección y oxidación. Puede utilizarse en mantenimiento o tratamientos de choque según formulación y necesidad.\n\nCONSIDERACIONES\nAporta calcio al agua y es un oxidante fuerte. Debe almacenarse seco y separado de materiales incompatibles.''',
             buenas_practicas='''• Dosificar según concentración real de la etiqueta.\n• Mantener utensilios limpios y dedicados.\n• Medir el agua y calcular por volumen.''',
             errores_comunes='''• Mezclar directamente con tricloro u otros productos concentrados.\n• Guardarlo húmedo.\n• Copiar una dosis de otro producto con distinta concentración.''',
             recomendaciones_jvaqua='''El Asistente Técnico debe trabajar con el producto exacto disponible y el volumen de la piscina; evita asumir que todos los “cloros granulados” tienen la misma concentración.''', etiquetas='hipoclorito calcio, cloro granulado, desinfectante, shock'),
        dict(codigo='AC-PRO-010', titulo='Ácido seco / reductor de pH', slug='acido-seco-reductor-ph', tipo='biblioteca', modulo_curso='productos', orden_curso=100, orden=100, nivel='intermedio', tiempo_lectura_min=7,
             resumen='Producto utilizado para reducir pH cuando corresponde. La dosis depende del volumen, lectura inicial, alcalinidad y formulación.',
             introduccion='''Un pH alto puede disminuir la eficacia operativa del cloro y favorecer incrustaciones. El reductor debe utilizarse de forma medida, nunca “a ojo”.''',
             contenido='''ANTES DE USAR\nConfirma pH, volumen y condición del agua. La alcalinidad influye en cuánto producto se necesita para mover el pH.\n\nAPLICACIÓN\nSigue la etiqueta del producto y distribuye según el procedimiento indicado. Permite circulación y vuelve a medir antes de repetir una corrección.''',
             buenas_practicas='''• Hacer correcciones graduales.\n• Mantener circulación adecuada.\n• Re-medición antes de una segunda dosis.''',
             errores_comunes='''• Añadir grandes cantidades de una vez.\n• Usar reductor sin haber medido.\n• Mezclar directamente con cloro u otros concentrados.''',
             recomendaciones_jvaqua='''En mantenimiento normal, el Asistente puede orientar la corrección de pH alto. En floculación con sulfato de aluminio, recuerda que el propio proceso puede bajar el pH y debe analizarse como un caso distinto.''', etiquetas='reductor ph, acido seco, ph alto, balance'),
        dict(codigo='AC-PRB-008', titulo='Incrustaciones blancas y sarro', slug='incrustaciones-sarro-piscina', tipo='biblioteca', modulo_curso='problemas', orden_curso=80, orden=80, nivel='intermedio', tiempo_lectura_min=8,
             resumen='Depósitos blancos en paredes, línea de agua o equipos pueden relacionarse con balance del agua y concentración de minerales.',
             introduccion='''Las incrustaciones no se resuelven simplemente cepillando una vez. Primero hay que identificar el depósito y revisar las condiciones que favorecen su formación.''',
             contenido='''QUÉ REVISAR\n• pH persistentemente alto.\n• Dureza cálcica y alcalinidad cuando el diagnóstico lo requiera.\n• Temperatura y evaporación.\n• Aspecto/localización del depósito.\n\nLa corrección depende del material de la piscina y de la causa. Algunos depósitos requieren tratamientos específicos que no deben improvisarse.''',
             buenas_practicas='''• Corregir la causa además de limpiar el depósito.\n• Probar cualquier método de limpieza en una zona pequeña.\n• Proteger acabados delicados.''',
             errores_comunes='''• Usar ácido fuerte directamente sobre cualquier superficie.\n• Confundir sarro con otra mancha.\n• Limpiar sin corregir el balance que lo produce.''',
             recomendaciones_jvaqua='''Si no puedes identificar el tipo de depósito o el acabado es delicado, documenta con fotografías y solicita diagnóstico antes de aplicar un tratamiento agresivo.''', etiquetas='sarro, incrustacion, calcio, manchas blancas, ph alto'),
        dict(codigo='AC-PRB-009', titulo='Manchas metálicas: cuándo sospechar de metales', slug='manchas-metales-piscina', tipo='biblioteca', modulo_curso='problemas', orden_curso=90, orden=90, nivel='avanzado', tiempo_lectura_min=8,
             resumen='Manchas marrones, verdosas o negras no siempre son algas. Aprende cuándo considerar hierro, cobre u otros metales como parte del diagnóstico.',
             introduccion='''El color por sí solo no confirma la causa. Metales disueltos pueden oxidarse y producir coloración o depósitos, pero también existen manchas orgánicas y problemas del acabado.''',
             contenido='''PISTAS\n• Aparición después de llenar con determinada fuente de agua.\n• Cambio de color tras oxidación/cloración.\n• Depósitos localizados que no se comportan como alga.\n\nDIAGNÓSTICO\nRevisa historia del agua, productos utilizados, equipos metálicos y, cuando corresponda, realiza pruebas específicas antes de tratar.''',
             buenas_practicas='''• Documentar color, ubicación y momento de aparición.\n• Evitar tratamientos agresivos sin diagnóstico.\n• Revisar si existen componentes de cobre/hierro deteriorados.''',
             errores_comunes='''• Aplicar alguicida a cualquier mancha verde.\n• Vaciar o acidificar sin conocer el acabado.\n• Asumir que todo color marrón es óxido.''',
             recomendaciones_jvaqua='''Usa el Asistente con fotografías/contexto cuando esté disponible, pero ante manchas persistentes conviene una evaluación específica antes de intervenir el acabado.''', etiquetas='metales, hierro, cobre, manchas, oxidacion'),
        dict(codigo='AC-ADV-002', titulo='Método de diagnóstico en 6 pasos', slug='metodo-diagnostico-piscina-seis-pasos', tipo='procedimiento', modulo_curso='avanzado', orden_curso=20, orden=20, nivel='avanzado', tiempo_lectura_min=10,
             resumen='Un método repetible para resolver problemas sin empezar a cambiar productos, válvulas y equipos al azar.',
             introduccion='''Los buenos diagnósticos siguen un orden. La meta no es adivinar rápido, sino reducir posibilidades hasta encontrar la causa más probable.''',
             procedimiento='''1. ESCUCHA EL SÍNTOMA: qué cambió y desde cuándo.\n2. OBSERVA: color, claridad, residuos, nivel, fugas, ruido y aire.\n3. MIDE: pH y CL; amplía parámetros cuando el caso lo requiera.\n4. REVISA CIRCULACIÓN: bomba cebada, canastillas, válvulas, retornos y presión.\n5. REVISA FILTRACIÓN: condición del filtro y mantenimiento reciente.\n6. ACTÚA Y VERIFICA: cambia una variable razonada, espera el tiempo necesario y comprueba el resultado.''',
             buenas_practicas='''• Registrar antes/después.\n• Empezar por comprobaciones simples.\n• Separar síntomas de causas.\n• Usar el Asistente para integrar los datos del caso.''',
             errores_comunes='''• Cambiar varias cosas simultáneamente.\n• Aplicar químicos sin comprobar circulación.\n• Reemplazar equipos sin descartar obstrucciones o configuración.''',
             recomendaciones_jvaqua='''Este método debe convertirse en hábito. Cuanto más ordenado sea el diagnóstico, menos producto, tiempo y repuestos se desperdician.''', etiquetas='diagnostico, metodo, problemas, avanzado, asistente tecnico'),
    ]
    for item in items:
        data = dict(item)
        data.update(estado='aprobado', version='1.0', acceso='compartido')
        Contenido.objects.update_or_create(codigo=data['codigo'], defaults=data)


def reverse(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    codigos = ['AC-FUN-006','AC-QUI-008','AC-SEG-004','AC-MAN-015','AC-EQP-012','AC-PRO-009','AC-PRO-010','AC-PRB-008','AC-PRB-009','AC-ADV-002']
    Contenido.objects.filter(codigo__in=codigos).delete()


class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0009_academia_visual_y_contenido_v2')]
    operations = [migrations.RunPython(seed, reverse)]
