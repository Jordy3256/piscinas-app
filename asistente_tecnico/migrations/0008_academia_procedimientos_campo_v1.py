from django.db import migrations


def seed_procedimientos(apps, schema_editor):
    Contenido = apps.get_model('asistente_tecnico', 'ContenidoAcademia')
    Consejo = apps.get_model('asistente_tecnico', 'ConsejoJVAQUA')

    def upsert(codigo, **data):
        defaults = {
            'tipo': data.pop('tipo', 'procedimiento'),
            'titulo': data.pop('titulo'),
            'slug': data.pop('slug'),
            'resumen': data.pop('resumen', ''),
            'nivel': data.pop('nivel', 'basico'),
            'tiempo_lectura_min': data.pop('tiempo_lectura_min', 6),
            'estado': 'aprobado',
            'version': '1.0',
            'acceso': data.pop('acceso', 'compartido'),
            'modulo_curso': data.pop('modulo_curso', 'mantenimiento'),
            'orden_curso': data.pop('orden_curso', 0),
            'orden': data.pop('orden', 0),
        }
        defaults.update(data)
        obj, _ = Contenido.objects.update_or_create(codigo=codigo, defaults=defaults)
        return obj

    items = [
        dict(codigo='PR-M-010', titulo='Preparación antes de aspirar', slug='preparacion-antes-aspirar', orden_curso=15,
             resumen='Cómo preparar manguera, aspiradora, succión y sistema antes de comenzar el aspirado.',
             herramientas_materiales='Cabezal de aspiración, pértiga, manguera, adaptador/plato de aspiración cuando corresponda y EPP básico.',
             procedimiento='1. Inspecciona el fondo y define si el residuo puede ir al filtro o debe aspirarse a desagüe.\n2. Conecta cabezal, pértiga y manguera.\n3. Llena completamente la manguera con agua para expulsar el aire.\n4. Conecta a la toma de aspiración o skimmer según la instalación.\n5. Ajusta válvulas solo si conoces la configuración hidráulica.\n6. Comprueba que la bomba permanezca cebada y exista caudal estable.\n7. Inicia el aspirado con movimientos lentos.',
             buenas_practicas='Mantén la manguera llena de agua antes de conectarla y vigila el nivel de piscina durante todo el trabajo.',
             errores_comunes='• Conectar una manguera llena de aire.\n• Aspirar demasiado rápido y volver a suspender la suciedad.\n• Cerrar demasiadas líneas de succión y provocar cavitación o pérdida de cebado.',
             recomendaciones_jvaqua='Antes de aspirar, JVAQUA determina primero el destino de la suciedad: filtración normal o desagüe, especialmente después de una floculación.', etiquetas='aspirado,manguera,cebado,succion,preparacion'),
        dict(codigo='PR-M-011', titulo='Aspirado a desagüe', slug='aspirado-a-desague', orden_curso=85, nivel='intermedio', tiempo_lectura_min=7,
             resumen='Procedimiento para retirar sedimento fino o flóculos sin enviarlos nuevamente al filtro.',
             herramientas_materiales='Equipo de aspiración, acceso seguro a desagüe y agua disponible para controlar el nivel cuando sea necesario.',
             procedimiento='1. Confirma que la instalación permite aspirar a desagüe.\n2. Apaga la bomba antes de cambiar una multiválvula.\n3. Coloca la válvula en WASTE/DESAGÜE según el fabricante.\n4. Verifica nivel de agua suficiente.\n5. Enciende la bomba y aspira muy lentamente sin levantar el sedimento.\n6. Vigila continuamente el nivel de la piscina.\n7. Apaga la bomba al terminar.\n8. Devuelve la válvula a la posición operativa correcta con la bomba apagada.\n9. Repón nivel de agua y restablece filtración.',
             buenas_practicas='Trabaja por zonas y evita movimientos bruscos. Detén el proceso antes de que el nivel de agua comprometa la succión.',
             errores_comunes='• Mover la multiválvula con la bomba encendida.\n• Dejar bajar demasiado el nivel.\n• Aspirar rápido y dispersar el flóculo.\n• Olvidar devolver el sistema a filtración.', etiquetas='aspirado,desague,waste,floculacion,sedimento'),
        dict(codigo='PR-M-012', titulo='Puesta en marcha después de una floculación', slug='puesta-marcha-despues-floculacion', orden_curso=87, nivel='intermedio',
             resumen='Cómo retirar el sedimento y devolver la piscina a operación después del tiempo de reposo.',
             procedimiento='1. Comprueba visualmente que el material se haya sedimentado.\n2. Evita ingresar o agitar el agua.\n3. Prepara aspirado a desagüe.\n4. Retira el sedimento lentamente.\n5. Repón el nivel de agua.\n6. Restablece circulación y filtración.\n7. Mide nuevamente pH y cloro.\n8. Corrige gradualmente si hace falta.\n9. Revisa claridad antes de considerar terminado el proceso.',
             buenas_practicas='La paciencia es parte del procedimiento: si se vuelve a suspender el sedimento, será más difícil retirarlo.',
             errores_comunes='• Encender circulación antes de retirar el sedimento.\n• Aspirar el flóculo hacia el filtro cuando el procedimiento requiere desagüe.\n• Dar por terminado el tratamiento sin volver a medir.', recomendaciones_jvaqua='JVAQUA prefiere un proceso de floculación cercano a 24 horas cuando las condiciones operativas lo permiten; 12–24 h puede ser aceptable según el caso.', etiquetas='floculacion,sedimento,aspirado,puesta en marcha'),
        dict(codigo='PR-M-013', titulo='Cebado correcto de una bomba', slug='cebado-correcto-bomba', orden_curso=55, nivel='intermedio',
             resumen='Secuencia segura para recuperar el cebado cuando una bomba ha perdido agua en la línea de succión.',
             procedimiento='1. Apaga la bomba.\n2. Comprueba que el nivel de piscina sea adecuado.\n3. Revisa canastillas y válvulas de succión.\n4. Libera presión según el equipo.\n5. Abre la tapa del prefiltro solo sin presión.\n6. Llena el cuerpo/prefiltro con agua cuando el modelo lo requiera.\n7. Revisa y asienta correctamente la junta de tapa.\n8. Cierra la tapa.\n9. Coloca válvulas en una configuración segura de arranque.\n10. Enciende y observa si recupera flujo dentro del tiempo indicado por el fabricante.\n11. Si no ceba, apaga y diagnostica entrada de aire u obstrucción.',
             buenas_practicas='Nunca permitas que una bomba trabaje prolongadamente en seco.',
             errores_comunes='• Insistir con la bomba funcionando sin agua.\n• Abrir la tapa con presión.\n• Ignorar una junta deteriorada o una entrada de aire.', etiquetas='bomba,cebado,prefiltro,aire,succion'),
        dict(codigo='PR-M-014', titulo='Limpieza de canastilla de skimmer', slug='limpieza-canastilla-skimmer', orden_curso=45,
             resumen='Retiro seguro de hojas y residuos que restringen la captación superficial.',
             procedimiento='1. Observa el nivel de agua y funcionamiento del skimmer.\n2. Si la instalación lo requiere, detén el sistema antes de retirar la canastilla.\n3. Retira tapa y canastilla.\n4. Elimina residuos.\n5. Revisa que la canastilla no esté rota.\n6. Reinstala correctamente.\n7. Comprueba nuevamente la succión y el flujo.',
             buenas_practicas='Una canastilla limpia protege la línea y reduce carga sobre la canastilla de la bomba.',
             errores_comunes='• Dejar residuos compactados.\n• Operar sin canastilla.\n• Forzar una canastilla rota o mal colocada.', etiquetas='skimmer,canastilla,limpieza,succion'),
        dict(codigo='PR-M-015', titulo='Limpieza básica de filtro de cartucho', slug='limpieza-filtro-cartucho', orden_curso=65, nivel='intermedio',
             resumen='Procedimiento general para retirar, inspeccionar y limpiar un cartucho sin dañar el elemento filtrante.',
             procedimiento='1. Apaga y bloquea el sistema para evitar arranque accidental.\n2. Libera completamente la presión según el fabricante.\n3. Abre el filtro solo cuando el manómetro indique cero y sea seguro.\n4. Retira el cartucho.\n5. Enjuaga entre pliegues con agua a presión moderada, de arriba hacia abajo.\n6. Inspecciona roturas, deformación y bandas.\n7. Limpia el interior del tanque y junta según corresponda.\n8. Reinstala correctamente.\n9. Cierra el filtro conforme al fabricante.\n10. Arranca y purga aire; revisa fugas y presión.',
             buenas_practicas='Respeta siempre el manual específico del filtro; los sistemas de cierre varían por fabricante.',
             errores_comunes='• Abrir un filtro presurizado.\n• Dañar los pliegues con presión excesiva.\n• Reinstalar un cartucho roto.\n• Arrancar sin purgar aire cuando el equipo lo requiere.', etiquetas='filtro cartucho,limpieza,presion,mantenimiento'),
        dict(codigo='PR-M-016', titulo='Revisión de nivel de agua', slug='revision-nivel-agua', orden_curso=12,
             resumen='Por qué el nivel correcto es esencial para skimmer, bomba, aspirado y funcionamiento hidráulico.',
             procedimiento='1. Observa el nivel antes de encender o manipular el sistema.\n2. Confirma que el skimmer pueda captar agua sin formar un vórtice de aire.\n3. Si el nivel es bajo, repón agua antes de procedimientos que aumenten el riesgo de pérdida de cebado.\n4. Si está excesivamente alto y afecta el skimmer, corrige según la instalación.\n5. Si existe pérdida recurrente, reporta para evaluar fuga, evaporación o uso.',
             errores_comunes='• Aspirar o retrolavar con nivel insuficiente.\n• Ignorar entrada de aire por el skimmer.\n• Asumir automáticamente que toda pérdida de nivel es una fuga.', etiquetas='nivel agua,skimmer,bomba,cebado'),
        dict(codigo='PR-M-017', titulo='Aplicación segura de productos químicos', slug='aplicacion-segura-productos-quimicos', modulo_curso='seguridad', orden_curso=30, nivel='intermedio',
             resumen='Reglas generales para manipular y aplicar productos sin mezclas incompatibles ni exposiciones innecesarias.',
             procedimiento='1. Lee etiqueta y ficha de seguridad del producto.\n2. Usa el EPP indicado.\n3. Confirma producto, concentración, volumen y dosis antes de abrirlo.\n4. Usa utensilios limpios y exclusivos cuando corresponda.\n5. Nunca mezcles productos químicos entre sí.\n6. Si un producto debe diluirse, sigue exactamente la etiqueta y el procedimiento aprobado.\n7. Aplica en un área ventilada y con circulación cuando el producto/proceso lo requiera.\n8. Cierra y almacena el envase correctamente.\n9. Lávate las manos después de manipular químicos.',
             buenas_practicas='Mantén cloros, ácidos y otros productos incompatibles separados y secos durante transporte y almacenamiento.',
             errores_comunes='• Usar el mismo recipiente para químicos incompatibles.\n• Mezclar productos “para ahorrar tiempo”.\n• Agregar agua a un producto cuando la etiqueta exige el orden contrario.\n• Trabajar sin protección adecuada.', etiquetas='seguridad,quimicos,epp,mezclas,cloro,acidos'),
        dict(codigo='PR-M-018', titulo='Diagnóstico rápido de baja presión en el filtro', slug='diagnostico-baja-presion-filtro', modulo_curso='problemas', orden_curso=70, nivel='intermedio',
             resumen='Una presión baja suele orientar la revisión hacia problemas de alimentación o caudal antes del filtro.',
             procedimiento='1. Confirma que el manómetro funcione.\n2. Revisa nivel de agua.\n3. Limpia skimmer y canastilla de bomba.\n4. Observa aire en el prefiltro.\n5. Comprueba válvulas de succión.\n6. Revisa pérdida de cebado u obstrucción.\n7. Si persiste, escala diagnóstico de impulsor, tubería o bomba.',
             buenas_practicas='Compara siempre con la presión normal de esa instalación.',
             errores_comunes='• Retrolavar porque la presión está baja.\n• Asumir que el filtro está sucio sin revisar succión.\n• Confiar en un manómetro trabado.', etiquetas='presion baja,filtro,bomba,succion,caudal'),
        dict(codigo='PR-M-019', titulo='Diagnóstico rápido de presión alta en el filtro', slug='diagnostico-presion-alta-filtro', modulo_curso='problemas', orden_curso=80, nivel='intermedio',
             resumen='Una presión elevada respecto de la referencia limpia puede indicar restricción en filtración o retorno.',
             procedimiento='1. Confirma lectura del manómetro.\n2. Compara con presión limpia habitual.\n3. Revisa posición de válvulas.\n4. Retrolava o limpia el filtro cuando corresponda al tipo de medio.\n5. Comprueba retornos y restricciones posteriores al filtro.\n6. Si la presión no normaliza, detén el diagnóstico superficial y revisa el equipo según fabricante.',
             errores_comunes='• Usar un número universal como presión “correcta”.\n• Abrir el filtro con presión.\n• Repetir retrolavados sin investigar una obstrucción persistente.', etiquetas='presion alta,filtro,retrolavado,retornos'),
        dict(codigo='PR-M-020', titulo='Qué hacer cuando entra aire a la bomba', slug='aire-en-bomba-diagnostico', modulo_curso='problemas', orden_curso=90, nivel='intermedio',
             resumen='Secuencia para localizar causas comunes de burbujas en el prefiltro o pérdida de cebado.',
             procedimiento='1. Revisa nivel de agua y skimmer.\n2. Comprueba tapa y junta del prefiltro.\n3. Observa uniones accesibles del lado de succión.\n4. Revisa válvulas y canastillas.\n5. Ceba nuevamente si corresponde.\n6. Si continúa entrando aire, reporta para prueba de succión/tubería.',
             buenas_practicas='Busca primero causas simples y visibles antes de desmontar componentes.',
             errores_comunes='• Sellar uniones al azar.\n• Dejar la bomba funcionando con flujo inestable.\n• Confundir burbujas temporales después de mantenimiento con una entrada permanente de aire.', etiquetas='aire,bomba,cebado,succion,burbujas'),
        dict(codigo='PR-M-021', titulo='Piscina sin circulación: respuesta inicial', slug='piscina-sin-circulacion-respuesta-inicial', modulo_curso='problemas', orden_curso=100, nivel='intermedio',
             resumen='Qué revisar antes de aplicar tratamientos cuando no existe circulación visible.',
             procedimiento='1. No comiences una dosificación rutinaria como si el sistema funcionara normalmente.\n2. Comprueba energía/estado del equipo sin intervenir partes eléctricas energizadas.\n3. Revisa nivel, válvulas y canastillas.\n4. Comprueba cebado.\n5. Observa manómetro y retornos.\n6. Si no se recupera el flujo con verificaciones básicas, escala la falla.\n7. Define el tratamiento químico considerando que no existe distribución normal del agua.',
             buenas_practicas='Resolver o identificar primero el problema hidráulico evita desperdiciar producto y generar concentraciones localizadas.',
             errores_comunes='• Aplicar una dosis grande esperando que “la bomba se arregle después”.\n• Trabajar eléctricamente sin capacitación.\n• Dejar una bomba sin cebado funcionando.', etiquetas='sin circulacion,bomba,filtro,diagnostico'),
    ]

    for item in items:
        code = item.pop('codigo')
        upsert(code, **item)

    relations = {
        'PR-M-010': ['PR-M-002', 'PR-M-011', 'PR-M-016'],
        'PR-M-011': ['PR-M-008', 'PR-M-012', 'EQ-003'],
        'PR-M-012': ['PR-M-008', 'PR-M-011', 'AC-Q-001', 'AC-Q-002'],
        'PR-M-013': ['EQ-001', 'PB-006', 'PR-M-005'],
        'PR-M-014': ['EQ-004', 'PR-M-016'],
        'PR-M-015': ['AC-F-002', 'PV-003'],
        'PR-M-016': ['EQ-004', 'PR-M-013'],
        'PR-M-017': ['SG-001', 'BT-Q-001', 'BT-Q-002'],
        'PR-M-018': ['PB-006', 'PV-003', 'PR-M-013'],
        'PR-M-019': ['PV-003', 'PR-M-006', 'EQ-002'],
        'PR-M-020': ['PB-006', 'PR-M-013', 'EQ-001'],
        'PR-M-021': ['PB-006', 'EQ-001', 'AC-F-002'],
    }
    for code, related_codes in relations.items():
        obj = Contenido.objects.filter(codigo=code).first()
        if obj:
            obj.relacionados.add(*Contenido.objects.filter(codigo__in=related_codes))

    consejos = [
        ('Antes de aspirar, decide a dónde irá la suciedad', 'Suciedad normal puede filtrarse; sedimento de floculación suele requerir aspirado a desagüe.', 'mantenimiento', 110),
        ('Nunca muevas una multiválvula con la bomba encendida', 'Apaga la bomba antes de cambiar de FILTRAR a RETROLAVAR, ENJUAGAR o DESAGÜE.', 'equipos', 120),
        ('Presión baja y presión alta no significan lo mismo', 'Baja presión orienta primero a succión/caudal; alta presión orienta a restricción de filtración o retorno.', 'diagnostico', 130),
    ]
    for titulo, texto, categoria, orden in consejos:
        Consejo.objects.update_or_create(titulo=titulo, defaults={'texto': texto, 'categoria': categoria, 'orden': orden, 'activo': True})


def reverse_seed(apps, schema_editor):
    # Preservamos contenidos y progreso si se revierte la migración.
    pass


class Migration(migrations.Migration):
    dependencies = [('asistente_tecnico', '0007_academia_problemas_preventivo_equipos_v1')]
    operations = [migrations.RunPython(seed_procedimientos, reverse_seed)]
