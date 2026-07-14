# Guion del video de presentación — VitalCore (máx. 5 minutos)

Recorrido narrado del proyecto. Cada escena indica **[PANTALLA]** (qué se
graba) y **[VOZ]** (el texto a decir, listo para leer). Tiempo total: ~4:50.

## Preparación antes de grabar (no sale en el video)

1. Levantar la API con `INICIAR_API.bat` y verificar que
   http://127.0.0.1:8000/docs responde. **Importante para quien graba desde
   la máquina de Luis: la VPN debe estar desconectada.** En cualquier otra
   máquina no hace falta nada especial.
2. Dejar abiertas estas pestañas, en orden:
   1. https://github.com/Luisguslg/vitalcore (README visible)
   2. `docs/documento_tecnico.md` en GitHub (se ve renderizado, con diagrama)
   3. `docs/diccionario_datos.md` en GitHub
   4. `logs/verificacion.log` en GitHub
   5. http://127.0.0.1:8000/docs (Swagger de la API)
   6. El archivo `vitalcore_dashboard.pbix` abierto en Power BI Desktop
      (recomendado: pulsar "Actualizar" con la API corriendo antes de grabar)
   7. `logs/tabla_latencias.md` en GitHub
   8. `docs/bitacora_ia.md` en GitHub
3. Hablar a ritmo normal; si una escena se pasa 5–10 segundos no importa,
   el margen total lo permite.

---

## Escena 1 — Apertura y repositorio (0:00 – 0:30)

**[PANTALLA]** Pestaña 1: portada del repo en GitHub. Hacer scroll lento por
el README: se ven la tabla de endpoints y la guía rápida.

**[VOZ]**
«Este es VitalCore, nuestra solución al Proyecto 2: una arquitectura de datos
operativa para una plataforma de salud digital, construida sobre MongoDB.
Todo el proyecto está en este repositorio público: el código de la API, los
scripts de carga de datos, el documento técnico, la bitácora de auditoría de
IA y las evidencias de rendimiento. El README explica cómo levantar el
sistema en cualquier máquina con dos clics: un script instala las
dependencias y otro arranca la API. La base de datos vive en MongoDB Atlas,
un clúster replicado de tres nodos en la nube, así que el sistema queda
funcional para quien lo clone.»

## Escena 2 — Selección del motor y Teorema CAP (0:30 – 1:20)

**[PANTALLA]** Pestaña 2: `docs/documento_tecnico.md`. Mostrar la tabla de
patrones de acceso (sección 1.1), luego bajar a 1.2 y detenerse en 1.3 (CAP).

**[VOZ]**
«La primera decisión del proyecto fue el motor, y la tomamos a partir de los
patrones de acceso, no al revés. Documentamos los cinco patrones críticos del
enunciado y evaluamos formalmente las alternativas. Elegimos MongoDB por tres
razones: primero, cuatro de los cinco patrones son consultas centradas en una
entidad con estructura heterogénea — historial clínico, pacientes por médico,
alertas — que es el terreno natural del modelo documental. Segundo, para la
telemetría usamos colecciones time series nativas de MongoDB, que comprimen y
optimizan las consultas por rango de tiempo, neutralizando la ventaja de
Cassandra, que descartamos porque exige duplicar datos en una tabla por
consulta y su modelo favorece disponibilidad sobre consistencia. Y tercero,
la red de referidos se resuelve con el operador de grafos $graphLookup, sin
necesidad de un segundo motor. En cuanto al Teorema CAP: nuestro replica set
es un sistema CP. Con write y read concern en majority, ante una partición de
red el sistema prefiere rechazar una escritura antes que confirmar un dato
clínico que podría divergir. En salud, leer una dosis o una lectura crítica
obsoleta cuesta más que reintentar una operación — ese es el compromiso que
defendemos.»

## Escena 3 — Esquema, embebido vs. referenciado e índices (1:20 – 2:10)

**[PANTALLA]** Misma pestaña: sección 2 (tabla de colecciones, embebido vs.
referenciado, anti-patrón, tabla de índices). Cambiar 5 segundos a la
pestaña 3 (diccionario de datos) y luego a la pestaña 4
(`logs/verificacion.log`) mostrando la línea del IXSCAN.

**[VOZ]**
«El esquema son siete colecciones diseñadas consulta por consulta. La
decisión clave es el patrón extended reference: cada paciente lleva embebida
su última lectura vital y su nivel de riesgo, actualizados atómicamente en la
ingesta — el documento es la unidad de atomicidad en MongoDB. Gracias a eso,
la vista del médico, que es la consulta más frecuente, se resuelve con un
único find indexado en lugar de agregar sobre doscientas mil lecturas. Lo que
crece sin límite — lecturas, consultas, alertas — va referenciado por
patientId y doctorId. El anti-patrón que evitamos fue trasladar el modelo
relacional normalizado a colecciones espejo unidas con $lookup. Cada índice
responde a un patrón concreto, y no es teoría: la verificación con explain
muestra IXSCAN sobre el índice del médico, examinando exactamente sesenta
documentos para devolver sesenta — cero desperdicio — con cero milisegundos
de ejecución en el servidor. El diccionario de datos completo también está en
el repositorio.»

## Escena 4 — Pipeline de ingesta con coherencia médica (2:10 – 2:45)

**[PANTALLA]** Pestaña 4: `logs/verificacion.log` completo (conteos OK).
Mostrar 5 segundos `scripts/seed.py` en GitHub (la tabla SENSORS al inicio).

**[VOZ]**
«La base se puebla con un solo script, reproducible porque usa semilla fija:
quinientos pacientes con perfiles heterogéneos, cincuenta médicos en seis
especialidades, doscientas mil lecturas exactas distribuidas en seis meses
simulados y mil consultas con notas de longitud variable. La coherencia
médica no es aleatoria: los rangos se calibraron con criterios clínicos
reales — los de la American Diabetes Association para glucemia y las
categorías de la AHA para presión arterial — y las anomalías corresponden a
la condición de cada paciente: los diabéticos generan picos de glucosa, los
pacientes con EPOC desaturan. Las alertas no se inventan: se derivan de
superar el umbral que el médico definió para ese paciente. La verificación
posterior a la carga confirma todos los volúmenes del enunciado.»

## Escena 5 — Demo en vivo de la API (2:45 – 3:50)

**[PANTALLA]** Pestaña 5: Swagger en http://127.0.0.1:8000/docs.
1. Ejecutar `GET /doctors/D001/patients` → respuesta con pacientes ordenados
   por riesgo, señalar `lastReading` dentro del primer paciente.
2. Ejecutar `GET /patients/P0001/readings?sensor=glucose&limit=10` →
   señalar `value`, `timestamp` e `isCritical` en las lecturas.
3. Ejecutar `POST /readings` con el body:
   `{"patientId": "P0007", "sensorType": "glucose", "value": 320}` →
   señalar `"isCritical": true` y el `alertId`.
4. Ejecutar `GET /alerts/active` → la alerta recién creada aparece de
   primera.

**[VOZ]**
«Ahora el sistema en vivo. Esta es la capa de consulta: una API REST con la
documentación interactiva generada automáticamente. Primero, la vista del
médico: pido los pacientes activos del doctor D001 y llegan ordenados por
nivel de riesgo, cada uno con su última lectura ya embebida — esta es la
consulta que el índice resuelve sin tocar la colección de telemetría. Segundo,
el dashboard de salud del paciente: las últimas lecturas de glucosa de un
paciente, cada una con su marca temporal y su indicador de criticidad, en una
sola consulta sobre la colección de series de tiempo. Y ahora el patrón de
alertas de extremo a extremo: inserto una lectura nueva, una glucosa de
trescientos veinte miligramos por decilitro para este paciente. La respuesta
confirma que superó el umbral definido por su médico y que se creó la alerta
en la misma operación. Y si consulto las alertas activas… ahí está, de
primera. Ese ciclo completo — lectura, evaluación de umbral, alerta visible —
tarda menos de trescientos milisegundos incluyendo el viaje a la nube.»

## Escena 6 — Dashboard en Power BI (3:50 – 4:20)

**[PANTALLA]** Pestaña 6: Power BI Desktop. Recorrer las tres páginas en
orden: **Pacientes** (tarjetas, torta por nivel de riesgo, alertas por
sensor) → **Doctores** (especialidades, cantidad de pacientes por doctor) →
**API** (tarjetas de latencia y tabla por endpoint). No hacer zoom en la
tarjeta "Total alertas activas" ni en la fila "Total" de la tabla de la
página API.

**[VOZ]**
«Sobre esa API construimos el panel de visualización en Power BI, con tres
vistas operativas: la de pacientes, con la distribución de los quinientos
pacientes por nivel de riesgo y la actividad de alertas por tipo de sensor;
la de doctores, con las seis especialidades, la carga de pacientes por médico
y las alertas por especialidad — concentradas en medicina general porque la
alerta siempre notifica al médico tratante del paciente; y la vista de
rendimiento de la API, donde se visualiza el KPI de tiempo promedio de
respuesta por consulta que exige el proyecto, alimentado por la colección de
métricas que el propio sistema registra en cada petición.»

## Escena 7 — KPIs medidos y bitácora de IA (4:20 – 4:50)

**[PANTALLA]** Pestaña 7: `logs/tabla_latencias.md` (tabla de latencias).
Luego 5 segundos en pestaña 8: `docs/bitacora_ia.md`.

**[VOZ]**
«El rendimiento está medido, no estimado: treinta iteraciones por patrón con
parámetros aleatorios. Filtrar las doscientas mil lecturas por paciente,
sensor y rango de fechas toma sesenta y dos milisegundos del lado del
servidor; la consulta más costosa, el historial clínico completo, se mantiene
por debajo de los doscientos ochenta de extremo a extremo. Finalmente, el
proyecto incluye la bitácora de auditoría de prompts que exige el enunciado:
cada uso de inteligencia artificial está registrado con lo que aceptamos, lo
que ajustamos, lo que rechazamos y cómo validamos técnicamente cada
resultado antes de incorporarlo.»

## Escena 8 — Cierre (4:50 – 5:00)

**[PANTALLA]** Volver a la pestaña 1 (portada del repo).

**[VOZ]**
«En resumen: un motor elegido desde los patrones de acceso, un esquema sin
anti-patrones relacionales, doscientas mil lecturas con sentido clínico y una
capa de consulta con rendimiento verificable. Todo está en el repositorio,
listo para clonarse y ejecutarse. Gracias.»
