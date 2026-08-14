# JVAQUA ERP v3.3.2 — Academia: Curso Base

## Cambios principales

- La Academia queda organizada definitivamente como **Aprender · Consultar · Resolver**.
- `Aprender` ahora muestra el curso agrupado por módulos con progreso por módulo y progreso general.
- Se agregó **Continuar curso**, que lleva al primer tema todavía no completado.
- Cada artículo del curso muestra el **siguiente tema recomendado**.
- Los cinco artículos químicos revisados previamente pasan a **Conocimiento Oficial JVAQUA v1.0** y forman parte del curso.
- Se agregó un primer bloque amplio de conocimiento aprobado sobre:
  - Fundamentos de piscina, circulación y medición.
  - pH, cloro libre, alcalinidad, CYA y dureza cálcica.
  - Hipoclorito de sodio, reductor/incrementador de pH y clarificante.
  - Inspección, aspirado, cepillado, recolección, canastilla de bomba, retrolavado, filos, floculación y cierre.
  - Bomba, filtro de arena y multiválvula.
  - Seguridad química y seguridad de equipos presurizados.
  - Estándar de servicio JVAQUA (contenido interno).
- Se agregaron consejos técnicos rotativos.
- Se añadieron los módulos de curso **Seguridad** y **Estándar JVAQUA**.

## Importante

- No se integra la Academia al flujo obligatorio de mantenimientos.
- La Academia sigue siendo una ayuda opcional de aprendizaje y consulta.
- El Asistente Técnico permanece como la herramienta principal para resolver casos y realizar cálculos.
- No se implementaron todavía cobros/suscripciones externas; la estructura de acceso compartido/interno/suscriptor sigue preparada para esa fase futura.

## Instalación

```powershell
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py collectstatic --noinput
```

La migración nueva incluida es:

`asistente_tecnico/migrations/0006_academia_curso_base_v1.py`
