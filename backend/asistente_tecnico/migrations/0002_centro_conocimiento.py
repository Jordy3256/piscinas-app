from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def seed_conocimiento(apps, schema_editor):
    Categoria = apps.get_model('asistente_tecnico', 'CategoriaAcademia')
    Leccion = apps.get_model('asistente_tecnico', 'LeccionAcademia')
    Articulo = apps.get_model('asistente_tecnico', 'ArticuloBiblioteca')
    Consejo = apps.get_model('asistente_tecnico', 'ConsejoJVAQUA')

    cats = [
        ('tratamiento-quimico', 'Tratamiento químico', '🧪', 'Fundamentos, productos y protocolos para el manejo químico del agua.', 10),
        ('mantenimiento', 'Mantenimiento', '🏊', 'Procedimiento operativo para dejar la piscina limpia, segura y correctamente revisada.', 20),
        ('equipos', 'Equipos', '⚙️', 'Bombas, filtros, multiválvulas y componentes principales del sistema.', 30),
        ('diagnostico', 'Diagnóstico', '🔧', 'Cómo reconocer problemas frecuentes y qué revisar antes de intervenir.', 40),
        ('seguridad', 'Seguridad', '🛡️', 'Buenas prácticas para trabajar con químicos, electricidad y equipos.', 50),
        ('procedimientos-jvaqua', 'Procedimientos JVAQUA', '👷', 'Estándares internos de servicio, comunicación, evidencias y reporte.', 60),
    ]
    catmap = {}
    for slug, nombre, icono, descripcion, orden in cats:
        obj, _ = Categoria.objects.get_or_create(slug=slug, defaults={'nombre': nombre, 'icono': icono, 'descripcion': descripcion, 'orden': orden, 'activa': True})
        catmap[slug] = obj

    lessons = [
        ('tratamiento-quimico', 'Medición correcta de pH y cloro', 'La medición inicial es la base de cualquier decisión química.', 'Mide pH y cloro antes de aplicar un tratamiento. Usa una muestra representativa del agua y compara el resultado con los rangos operativos. En mantenimiento normal, el pH recomendado está entre 7.2 y 7.6 y el cloro entre 1 y 3 ppm, buscando aproximadamente 1.5 ppm.', 'No dosificar químicos importantes sin medir primero. No asumir que una piscina transparente tiene parámetros correctos.', 'Vuelve a medir después de una corrección importante antes de repetir dosis.', 8, 10),
        ('tratamiento-quimico', 'Cloro y desinfección', 'Cómo decidir entre tricloro y cloro granulado.', 'En agua transparente y estable se prioriza tricloro en pastilla para sostener el nivel de cloro. En turbidez ligera o tratamientos correctivos puede requerirse cloro granulado. En floculación, el shock busca aproximadamente 3–4 ppm.', 'No aplicar dosis repetidas sin verificar la respuesta del agua. Evita mezclar productos directamente entre sí.', 'En piscinas de alto uso la demanda de cloro puede ser mucho mayor y requerir aplicaciones más frecuentes.', 10, 20),
        ('tratamiento-quimico', 'Cómo subir el pH', 'Uso gradual de metasilicato y cal P24.', 'En mantenimiento normal, si el pH está bajo se puede usar metasilicato granulado de forma gradual, preferiblemente disuelto. Como referencia operativa, un puñado por cada 10 m³ puede ser suficiente; deja filtrar alrededor de 10 minutos y vuelve a medir. En una floculación con pH bajo puede usarse cal P24/soda en polvo, aproximadamente 250–350 g por 25 m³ según qué tan bajo esté el pH.', 'No aplicar toda una corrección grande de una sola vez sin volver a medir.', 'En floculación se puede llevar el pH aproximadamente a 7.8 antes del sulfato, porque el sulfato tenderá a bajarlo.', 10, 30),
        ('tratamiento-quimico', 'Cómo bajar el pH', 'Cuándo realmente hace falta un reductor.', 'En una piscina transparente con pH apenas elevado, primero puede bastar el tricloro, que tiende a bajar el pH con el tiempo. Si el pH está demasiado elevado en mantenimiento normal, se usa reductor de pH gradualmente. Como referencia operativa, un puñado por 25 m³ y nueva medición antes de repetir.', 'No usar reductor de pH como corrección previa durante una floculación con sulfato de aluminio.', 'El sulfato de aluminio ya tiende a reducir el pH durante la floculación.', 8, 40),
        ('tratamiento-quimico', 'Floculación con sulfato de aluminio', 'Protocolo para agua muy turbia o verde.', 'Cuando el agua está muy turbia o verde, se utiliza un tratamiento de choque con floculación. Mide pH y cloro. Si el pH está bajo, corrígelo primero. Realiza shock de cloro a 3–4 ppm, aplica sulfato de aluminio y deja reposar preferiblemente 24 horas. Después aspira el sedimento, realiza retrolavado y vuelve a medir. Referencia de sulfato: 1 kg por cada 25 m³ con tolerancia aproximada de ±5 m³; si se supera claramente el tramo, se usa el siguiente kg entero.', 'No activar filtración durante el tiempo de sedimentación si el protocolo requiere reposo. No combinar reductor con sulfato por rutina.', '24 horas es la recomendación preferida para permitir una buena sedimentación.', 15, 50),
        ('tratamiento-quimico', 'Alguicida en tratamiento de choque', 'Uso complementario del alguicida.', 'En un tratamiento de choque puede utilizarse alguicida como apoyo. La referencia operativa JVAQUA es aproximadamente 50 g por cada 25 m³. No sustituye al cloro ni al proceso de floculación cuando el agua está muy turbia o verde.', 'No considerar el alguicida como sustituto de una desinfección adecuada.', 'La causa del agua verde debe tratarse de forma integral: cloro, pH, limpieza, filtración y floculación cuando corresponda.', 6, 60),
        ('mantenimiento', 'Inspección inicial', 'Qué revisar antes de comenzar.', 'Antes de limpiar revisa el estado del agua, pH y cloro, funcionamiento de la bomba, estado del filtro y nivel de agua. Esta inspección ayuda a detectar novedades antes de manipular el sistema.', 'No comenzar un procedimiento que dependa de circulación si la bomba presenta una falla evidente.', 'Una inspección de un minuto puede evitar una intervención incorrecta o daño de equipos.', 6, 10),
        ('mantenimiento', 'Aspirado correcto', 'Cómo retirar suciedad del fondo sin perder eficiencia.', 'Aspira de forma ordenada, evitando movimientos bruscos que levanten el sedimento. Comprueba que exista buena succión y controla el nivel de agua durante el proceso.', 'No aspirar demasiado rápido cuando hay sedimento fino. No dejar que la bomba trabaje sin agua.', 'En una floculación, el sedimento debe aspirarse con especial cuidado para no volver a suspenderlo.', 7, 20),
        ('mantenimiento', 'Cepillado y limpieza de filos', 'Evita acumulaciones en paredes y línea de agua.', 'Cepilla paredes, escalones y zonas de poca circulación. Limpia los filos y la línea de agua donde se acumulan grasas y residuos. El cepillado ayuda a desprender material para que pueda aspirarse o filtrarse.', 'No dejar zonas detrás de escaleras, esquinas o retornos sin revisar.', 'Las zonas con menor circulación suelen mostrar primero problemas de algas o suciedad adherida.', 6, 30),
        ('mantenimiento', 'Retrolavado de arena', 'Cuándo y cómo limpiar el filtro.', 'Realiza retrolavado cuando la presión del filtro y el comportamiento del caudal indiquen acumulación de suciedad o después de procesos que cargan fuertemente el filtro. Sigue la secuencia correcta de la multiválvula con la bomba apagada al cambiar de posición.', 'Nunca mover la multiválvula con la bomba funcionando.', 'Después del retrolavado, verifica presión y caudal para confirmar que el sistema volvió a trabajar normalmente.', 8, 40),
        ('equipos', 'Funcionamiento básico de la bomba', 'Qué hace la bomba y qué señales observar.', 'La bomba hace circular el agua a través del sistema de filtración. Revisa sonido, cebado, caudal, posibles fugas y presencia de aire. Una bomba que no succiona puede tener problemas de cebado, entradas de aire, obstrucciones o nivel de agua insuficiente.', 'No dejar una bomba trabajando en seco.', 'Antes de asumir una avería, revisa nivel de agua, canastillas y posibles entradas de aire.', 9, 10),
        ('equipos', 'Filtro de arena', 'Cómo trabaja y cuándo requiere atención.', 'El filtro retiene partículas mientras el agua atraviesa el medio filtrante. La presión y el caudal ayudan a identificar cuándo necesita retrolavado. La arena pierde eficiencia con el tiempo y debe revisarse periódicamente.', 'No interpretar solo el manómetro: observa también el caudal y el estado general del agua.', 'JVAQUA recomienda el cambio de arena aproximadamente una vez al año como referencia de mantenimiento preventivo.', 9, 20),
        ('equipos', 'Multiválvula', 'Posiciones y cuidado básico.', 'La multiválvula dirige el flujo hacia filtración, retrolavado, enjuague, desagüe u otras funciones según el modelo. Cada cambio de posición debe hacerse con la bomba apagada.', 'Nunca forzar la palanca ni cambiar posiciones con la bomba encendida.', 'Una fuga o funcionamiento extraño después de cambiar posiciones puede indicar desgaste interno o un problema de asiento.', 7, 30),
        ('equipos', 'Skimmers, retornos y drenajes', 'Cómo participan en la circulación.', 'Los skimmers captan residuos de superficie; los retornos devuelven el agua filtrada; los drenajes ayudan a la captación desde zonas bajas. Una circulación equilibrada mejora la filtración y distribución química.', 'No ignorar canastillas obstruidas o retornos con caudal muy desigual.', 'La mala circulación puede parecer un problema químico aunque el origen sea hidráulico.', 7, 40),
        ('diagnostico', 'Agua verde', 'Qué revisar antes de decidir el tratamiento.', 'El agua verde suele indicar crecimiento de algas y pérdida de control de desinfección. Mide pH y cloro, revisa circulación y suciedad. Cuando está claramente verde, el protocolo JVAQUA utiliza tratamiento de choque y floculación.', 'No intentar resolver una piscina verde únicamente con pequeñas dosis de mantenimiento.', 'Usa el Asistente Técnico para calcular el protocolo según volumen y parámetros reales.', 9, 10),
        ('diagnostico', 'Agua ligeramente turbia', 'Diferenciar una corrección simple de una floculación.', 'Si la turbidez es ligera, no siempre hace falta sulfato. Revisa pH y cloro, limpia, filtra y puede ser necesario un shock moderado con cloro granulado. Observa la respuesta antes de escalar a una floculación completa.', 'No usar sulfato automáticamente ante cualquier pérdida de transparencia.', 'Clasificar correctamente el estado del agua evita tratamientos innecesarios.', 8, 20),
        ('diagnostico', 'Bomba que no succiona', 'Lista básica de revisión.', 'Comprueba nivel de agua, cebado, tapa y sello del prefiltro, canastilla, posición de válvulas y posibles entradas de aire en la succión. Si no recupera cebado, reporta la novedad antes de forzar el equipo.', 'No mantener la bomba encendida en seco esperando que succione sola.', 'Documenta la novedad y escala a administración si requiere reparación.', 8, 30),
        ('diagnostico', 'Presión alta en el filtro', 'Qué puede estar ocurriendo.', 'Una presión por encima de la referencia habitual puede indicar filtro cargado, obstrucción o restricción en el retorno. Revisa el estado del filtro y realiza retrolavado cuando corresponda.', 'No asumir que toda lectura alta es problema del manómetro sin revisar el sistema.', 'Compara siempre contra el comportamiento normal de esa piscina.', 7, 40),
        ('seguridad', 'Manipulación segura de químicos', 'Reglas esenciales para trabajar con productos de piscina.', 'Utiliza protección adecuada, mantén los envases identificados y evita contacto directo. Añade los productos por separado siguiendo el procedimiento de cada uno. Mantén los químicos cerrados, secos y ventilados durante transporte y almacenamiento.', 'Nunca mezclar químicos concentrados directamente entre sí. No reutilizar recipientes sin identificar.', 'Si existe una condición que no conoces o no es segura, detén el procedimiento y consulta a administración.', 10, 10),
        ('seguridad', 'Seguridad con bombas y electricidad', 'Precauciones antes de manipular equipos.', 'Evita intervenir equipos eléctricos mojados o con conexiones inseguras. Apaga la bomba antes de manipular multiválvulas, canastillas o elementos que requieran apertura del circuito.', 'No improvisar reparaciones eléctricas sin la capacitación correspondiente.', 'Una novedad de seguridad se reporta antes de continuar el mantenimiento.', 8, 20),
        ('seguridad', 'Transporte y almacenamiento de productos', 'Cómo reducir riesgos durante el trabajo de campo.', 'Transporta los productos cerrados, separados y evitando exposición excesiva a calor o humedad. Mantén etiquetas visibles y evita transportar productos incompatibles abiertos o sin protección.', 'No dejar químicos sueltos, sin tapa o en recipientes no identificados.', 'El orden del inventario del técnico también es una medida de seguridad.', 7, 30),
        ('procedimientos-jvaqua', 'Orden estándar de mantenimiento', 'La secuencia operativa recomendada por JVAQUA.', 'El flujo estándar comienza con inspección y parámetros, continúa con aspirado, cepillado, recolección de basura, limpieza de canastillas y filtros, tratamiento químico y revisión final. Registra en la aplicación lo realmente realizado.', 'No marcar actividades que no se realizaron. Las tres fotografías requeridas deben corresponder al servicio real.', 'La consistencia del procedimiento facilita el control de calidad y el historial de cada piscina.', 8, 10),
        ('procedimientos-jvaqua', 'Contacto por WhatsApp en domicilio', 'Cuándo utilizar el acceso rápido al cliente.', 'El acceso rápido de WhatsApp está pensado para cuando el técnico ya se encuentra en el domicilio y no obtiene respuesta, especialmente si administración tampoco logra contactar al cliente. El mensaje se prepara con el nombre del técnico y debe revisarse antes de enviarlo.', 'No utilizar esta función para comunicaciones innecesarias o frecuentes con el cliente.', 'La llamada directa no forma parte del acceso rápido estándar; se prioriza un mensaje respetuoso por WhatsApp.', 5, 20),
        ('procedimientos-jvaqua', 'Fotografías y cierre del mantenimiento', 'Cómo dejar evidencia útil del servicio.', 'Toma la fotografía antes de iniciar, después de finalizar y la evidencia de pH/CL final. Procura buena iluminación y que la imagen permita comprender el estado real de la piscina o medición.', 'No subir fotografías borrosas, repetidas o que no correspondan a la visita.', 'Las fotos son la evidencia obligatoria del cierre; el resto del checklist es una ayuda operativa y puede ser opcional.', 6, 30),
    ]
    for slug, titulo, resumen, contenido, errores, consejo, duracion, orden in lessons:
        Leccion.objects.get_or_create(categoria=catmap[slug], titulo=titulo, defaults={'resumen': resumen, 'contenido': contenido, 'errores_evitar': errores, 'consejo_jvaqua': consejo, 'duracion_minutos': duracion, 'orden': orden, 'publicada': True})

    articles = [
        ('Bomba de piscina', 'equipos', 'Equipo encargado de mover el agua a través del circuito de filtración.', 'Aspira agua desde la piscina y la impulsa a través del filtro y retornos.', 'Motor, prefiltro/canastilla, impulsor, tapa, sellos y conexiones.', 'Mantén la canastilla limpia, revisa cebado, fugas y sonidos anormales.', 'No succiona, entra aire, pierde agua, ruido anormal, poco caudal.', 'Nunca debe trabajar en seco. Revisa primero nivel de agua y obstrucciones.', 'bomba motor cebado succion aire caudal'),
        ('Filtro de arena', 'filtracion', 'Retiene partículas suspendidas utilizando arena u otro medio filtrante.', 'El agua atraviesa el medio filtrante y devuelve agua más limpia a la piscina.', 'Tanque, arena/medio filtrante, colectores, manómetro y multiválvula según sistema.', 'Retrolava según presión y caudal. Revisa el estado del medio filtrante.', 'Presión alta, bajo caudal, agua que no aclara, arena que retorna a piscina.', 'Como referencia JVAQUA, revisa/cambia la arena preventivamente aproximadamente una vez al año.', 'filtro arena presion manometro retrolavado'),
        ('Multiválvula', 'equipos', 'Controla el recorrido del agua en filtros de arena.', 'Cambia el circuito entre filtración, retrolavado, enjuague, desagüe y otras funciones según modelo.', 'Palanca, rotor/selector, junta interna y conexiones.', 'Cambiar de posición únicamente con la bomba apagada.', 'Fugas, posiciones que no sellan, palanca floja o dura, flujo incorrecto.', 'No forzar ni mover con presión del sistema.', 'multivalvula valvula filtro posiciones retrolavado'),
        ('Tricloro en pastilla', 'quimica', 'Desinfectante de liberación sostenida usado principalmente en mantenimiento.', 'Libera cloro de forma gradual y suele tender a reducir ligeramente el pH.', 'Pastillas según presentación comercial.', 'Controla pH y cloro; ajusta cantidad/frecuencia según demanda de la piscina.', 'Cloro insuficiente en piscinas de alto uso si se depende únicamente de pastillas.', 'Priorizar en agua transparente y estable cuando la demanda permite mantenimiento sostenido.', 'tricloro pastilla cloro mantenimiento'),
        ('Sulfato de aluminio', 'quimica', 'Floculante principal del protocolo JVAQUA para agua muy turbia o verde.', 'Agrupa partículas suspendidas para facilitar su sedimentación y además tiende a disminuir el pH.', '', 'Se utiliza dentro de un protocolo de floculación, no como producto rutinario para toda turbidez.', 'Exceso, mala clasificación del agua, no corregir pH bajo previamente, aspirar mal el sedimento.', 'Referencia operativa: 1 kg por 25 m³ con tolerancia aproximada de ±5 m³ y 24 h de reposo preferido.', 'sulfato aluminio floculante floculacion agua verde turbia'),
        ('Metasilicato', 'quimica', 'Producto utilizado por JVAQUA para elevar el pH en mantenimiento normal.', 'Incrementa gradualmente el pH según la dosis y condiciones del agua.', '', 'Aplicar preferiblemente disuelto, de forma gradual, dejar recircular unos 10 minutos y volver a medir.', 'Aplicar demasiado sin medir nuevamente.', 'Referencia operativa: aproximadamente un puñado por 10 m³, siempre comprobando la respuesta.', 'metasilicato subir ph alcalino'),
        ('Agua verde', 'diagnostico', 'Estado que normalmente requiere un tratamiento correctivo de choque.', 'La combinación de desinfección insuficiente, algas y condiciones de circulación puede provocar el color verde.', '', 'Mide pH y cloro, revisa circulación y usa el Asistente Técnico para el protocolo de choque/floculación.', 'Aplicar solo pequeñas dosis de mantenimiento o ignorar el pH inicial.', 'El protocolo JVAQUA prioriza shock de cloro, sulfato y reposo cuando el agua está claramente verde.', 'agua verde algas choque floculacion'),
        ('Retrolavado', 'mantenimiento', 'Procedimiento para limpiar el medio filtrante invirtiendo el flujo.', 'El agua arrastra suciedad acumulada dentro del filtro hacia desagüe.', 'Bomba, filtro y multiválvula/valvulería correspondiente.', 'Apaga la bomba antes de cambiar posiciones; verifica presión y caudal después.', 'Mover la multiválvula con la bomba encendida.', 'Úsalo cuando presión/caudal y condición del filtro indiquen que es necesario.', 'retrolavado filtro arena limpiar'),
        ('Skimmer', 'equipos', 'Captación superficial que ayuda a retirar residuos flotantes.', 'El agua entra por el skimmer y lleva residuos hacia la canastilla y sistema de filtración.', 'Boca, compuerta, canastilla y tubería de succión.', 'Mantén la canastilla limpia y verifica que el nivel de agua permita buena captación.', 'Bajo nivel de agua, canastilla obstruida, entrada de aire.', 'Un skimmer obstruido puede reducir caudal y afectar el cebado.', 'skimmer canastilla superficie succion'),
        ('pH de piscina', 'quimica', 'Indicador de acidez/alcalinidad que afecta comodidad y eficacia del tratamiento.', 'El pH influye en el comportamiento del cloro y otros productos.', '', 'En mantenimiento normal JVAQUA trabaja como referencia entre 7.2 y 7.6.', 'Corregir sin medir o intentar cambios bruscos.', 'En floculación el objetivo previo puede ser diferente por la caída de pH provocada por el sulfato.', 'ph medir rango agua'),
        ('Cloro de piscina', 'quimica', 'Desinfectante principal para controlar microorganismos y mantener el agua segura.', 'El cloro disponible se consume por bañistas, materia orgánica, radiación y otras cargas.', '', 'En mantenimiento normal se busca 1–3 ppm, ideal operativo alrededor de 1.5 ppm; en shock de floculación, 3–4 ppm.', 'Repetir dosis sin medir, mezclar directamente con otros químicos.', 'Piscinas de alto uso pueden necesitar aportes más frecuentes y cloro granulado.', 'cloro ppm desinfeccion shock'),
        ('Bomba que no succiona', 'diagnostico', 'Guía rápida ante una bomba que pierde o no logra cebado.', 'La causa puede estar en nivel de agua, obstrucción, válvulas, canastilla, sello de tapa o entrada de aire.', '', 'Apaga si trabaja en seco. Revisa nivel, prefiltro, tapa, válvulas y posibles entradas de aire.', 'Mantenerla encendida esperando que recupere cebado sin agua.', 'Si no se identifica una causa segura y simple, reporta a administración para revisión técnica.', 'bomba no succiona no ceba aire'),
    ]
    for titulo, categoria, resumen, funcionamiento, componentes, mantenimiento, fallas, recomendaciones, claves in articles:
        Articulo.objects.get_or_create(titulo=titulo, defaults={'categoria': categoria, 'resumen': resumen, 'funcionamiento': funcionamiento, 'componentes': componentes, 'mantenimiento': mantenimiento, 'fallas_comunes': fallas, 'recomendaciones': recomendaciones, 'palabras_clave': claves, 'publicada': True})

    consejos = [
        ('Mide antes de dosificar', 'Antes de aplicar un tratamiento químico importante, mide pH y cloro. La medición evita correcciones innecesarias.', 'quimica'),
        ('Cuida la bomba', 'Nunca dejes una bomba trabajando en seco. Si pierde cebado, revisa la causa antes de continuar.', 'equipos'),
        ('Floculación', 'En agua muy turbia o verde, recuerda que el sulfato de aluminio también tiende a bajar el pH.', 'quimica'),
        ('Retrolavado seguro', 'Apaga siempre la bomba antes de cambiar la posición de una multiválvula.', 'seguridad'),
        ('Registro real', 'Marca únicamente las actividades que realmente realizaste; las fotografías deben corresponder a la visita.', 'procedimientos'),
        ('Correcciones graduales', 'Al subir o bajar pH, aplica de forma gradual y vuelve a medir antes de repetir una dosis.', 'quimica'),
        ('Observa el caudal', 'Presión y caudal juntos dan una mejor idea del estado del filtro que cualquiera de los dos por separado.', 'filtracion'),
        ('Agua transparente', 'Una piscina transparente también necesita medición: el aspecto visual no confirma por sí solo pH y cloro correctos.', 'mantenimiento'),
        ('Alto uso', 'En urbanizaciones y piscinas de alto uso, la demanda de cloro puede ser mucho mayor que en una piscina residencial.', 'quimica'),
        ('Sedimento de floculación', 'Después de flocular, aspira lentamente para evitar volver a suspender las partículas sedimentadas.', 'mantenimiento'),
        ('Seguridad química', 'Nunca mezcles productos químicos concentrados directamente entre sí.', 'seguridad'),
        ('Comunicación', 'Usa el acceso de WhatsApp al cliente solo cuando sea necesario para resolver el acceso al domicilio de forma profesional.', 'procedimientos'),
    ]
    for i, (titulo, texto, categoria) in enumerate(consejos, start=1):
        Consejo.objects.get_or_create(titulo=titulo, defaults={'texto': texto, 'categoria': categoria, 'activo': True, 'orden': i * 10})


def unseed_conocimiento(apps, schema_editor):
    # No eliminar contenido: puede haber sido editado por administración después de instalar la migración.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('asistente_tecnico', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaAcademia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('descripcion', models.CharField(blank=True, default='', max_length=240)),
                ('icono', models.CharField(blank=True, default='📘', max_length=20)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('activa', models.BooleanField(db_index=True, default=True)),
            ],
            options={'verbose_name': 'Categoría de academia', 'verbose_name_plural': 'Categorías de academia', 'ordering': ['orden', 'nombre']},
        ),
        migrations.CreateModel(
            name='ArticuloBiblioteca',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=160, unique=True)),
                ('categoria', models.CharField(choices=[('quimica', 'Química'), ('equipos', 'Equipos'), ('filtracion', 'Filtración'), ('mantenimiento', 'Mantenimiento'), ('diagnostico', 'Diagnóstico'), ('seguridad', 'Seguridad'), ('procedimientos', 'Procedimientos JVAQUA')], db_index=True, default='equipos', max_length=30)),
                ('resumen', models.CharField(blank=True, default='', max_length=280)),
                ('funcionamiento', models.TextField(blank=True, default='')),
                ('componentes', models.TextField(blank=True, default='')),
                ('mantenimiento', models.TextField(blank=True, default='')),
                ('fallas_comunes', models.TextField(blank=True, default='')),
                ('recomendaciones', models.TextField(blank=True, default='')),
                ('palabras_clave', models.CharField(blank=True, default='', max_length=300)),
                ('publicada', models.BooleanField(db_index=True, default=True)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='articulos_biblioteca_creados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Artículo de biblioteca', 'verbose_name_plural': 'Artículos de biblioteca', 'ordering': ['categoria', 'orden', 'titulo']},
        ),
        migrations.CreateModel(
            name='ConsejoJVAQUA',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(blank=True, default='Consejo JVAQUA', max_length=140)),
                ('texto', models.TextField()),
                ('categoria', models.CharField(choices=[('quimica', 'Química'), ('equipos', 'Equipos'), ('filtracion', 'Filtración'), ('mantenimiento', 'Mantenimiento'), ('diagnostico', 'Diagnóstico'), ('seguridad', 'Seguridad'), ('procedimientos', 'Procedimientos JVAQUA')], db_index=True, default='mantenimiento', max_length=30)),
                ('activo', models.BooleanField(db_index=True, default=True)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Consejo JVAQUA', 'verbose_name_plural': 'Consejos JVAQUA', 'ordering': ['orden', 'id']},
        ),
        migrations.CreateModel(
            name='LeccionAcademia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=160)),
                ('resumen', models.CharField(blank=True, default='', max_length=280)),
                ('contenido', models.TextField()),
                ('errores_evitar', models.TextField(blank=True, default='')),
                ('consejo_jvaqua', models.TextField(blank=True, default='')),
                ('duracion_minutos', models.PositiveSmallIntegerField(default=5)),
                ('orden', models.PositiveSmallIntegerField(default=0)),
                ('publicada', models.BooleanField(db_index=True, default=True)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lecciones', to='asistente_tecnico.categoriaacademia')),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lecciones_academia_creadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Lección de academia', 'verbose_name_plural': 'Lecciones de academia', 'ordering': ['categoria__orden', 'categoria__nombre', 'orden', 'titulo']},
        ),
        migrations.CreateModel(
            name='PropuestaConocimiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=180)),
                ('descripcion', models.TextField()),
                ('fuente_clave', models.CharField(max_length=160, unique=True)),
                ('evidencia', models.JSONField(blank=True, default=dict)),
                ('estado', models.CharField(choices=[('evaluacion', 'En evaluación'), ('aprobada', 'Aprobada'), ('descartada', 'Descartada')], db_index=True, default='evaluacion', max_length=20)),
                ('creado_en', models.DateTimeField(auto_now_add=True)),
                ('actualizado_en', models.DateTimeField(auto_now=True)),
                ('revisado_en', models.DateTimeField(blank=True, null=True)),
                ('nota_revision', models.TextField(blank=True, default='')),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='propuestas_conocimiento_revisadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Propuesta de conocimiento', 'verbose_name_plural': 'Propuestas de conocimiento', 'ordering': ['estado', '-actualizado_en']},
        ),
        migrations.CreateModel(
            name='ProgresoLeccion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completada', models.BooleanField(default=True)),
                ('completada_en', models.DateTimeField(default=django.utils.timezone.now)),
                ('leccion', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progresos', to='asistente_tecnico.leccionacademia')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='progreso_academia', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-completada_en']},
        ),
        migrations.AddConstraint(model_name='leccionacademia', constraint=models.UniqueConstraint(fields=('categoria', 'titulo'), name='ati_unique_lesson_category_title')),
        migrations.AddConstraint(model_name='progresoleccion', constraint=models.UniqueConstraint(fields=('user', 'leccion'), name='ati_unique_user_lesson_progress')),
        migrations.RunPython(seed_conocimiento, unseed_conocimiento),
    ]
