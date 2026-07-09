# Bitácora de Auditoría de Prompts — VitalCore

Registro de las interacciones con herramientas de IA generativa durante el
proyecto, conforme al punto 4.2 del enunciado. Cada entrada documenta el
prompt (resumido), la respuesta relevante, la **decisión** (aceptado /
ajustado / rechazado) y la **validación técnica** con la que se comprobó que
la sugerencia cumplía los requisitos antes de incorporarla.

---

## Entrada 1 — Contraste de familias NoSQL para los patrones de acceso

- **Fecha:** 2026-07-09 · **Herramienta:** OpenAI Codex (GPT-5.5)
- **Prompt (resumen):** «Los patrones de acceso del enunciado son mayormente
  operativos y centrados en el paciente (historial cronológico, telemetría
  por rango de fechas, cartera de pacientes por médico, alertas por umbral,
  red de referidos). Contrástame las cuatro familias NoSQL frente a esos
  patrones y dame una recomendación fundamentada; el caso es gestión
  operativa, no un ambiente analítico tipo DW.»
- **Respuesta:** recomendó MongoDB (documental) como motor principal, con
  Cassandra/ScyllaDB como alternativa a evaluar formalmente para la
  telemetría; citó documentación oficial (time series collections,
  replicación, niveles de consistencia).
- **Decisión: ACEPTADO.** 4 de los 5 patrones mínimos son consultas por
  entidad con estructura heterogénea, el terreno natural del modelo
  documental; el quinto (referidos) se cubre con `$graphLookup` sin
  incorporar un segundo motor, respetando el criterio de profundidad sobre
  amplitud del enunciado.
- **Validación:** se contrastaron las capacidades citadas contra la
  documentación oficial de MongoDB (time series, `$graphLookup`,
  `writeConcern`/`readConcern`) y se verificó que cada patrón del enunciado
  tuviera una estrategia concreta en el motor antes de fijar la decisión.
  El descarte de Cassandra se argumentó por su modelo de una tabla por
  consulta (duplicación mantenida a mano) y su orientación AP, menos
  adecuada para datos clínicos donde una lectura obsoleta tiene costo médico.

## Entrada 2 — Arquitectura: alertas, modelado y compromiso CAP

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Prompt (resumen):** «Con MongoDB decidido: ¿cómo estructuro colecciones e
  índices para que cada patrón de acceso sea una consulta indexada y no
  termine simulando joins relacionales con `$lookup`? ¿Y cómo defiendo el
  compromiso CAP del replica set con write/read concern majority para el
  contexto salud?»
- **Respuesta:** propuso el esquema de 6 colecciones (time series para
  telemetría con `metaField {patientId, sensorType}`), change streams para
  alertas en tiempo real, y la argumentación CP: ante partición, el lado sin
  mayoría rechaza escrituras antes que confirmar datos clínicos que podrían
  divergir.
- **Decisiones:**
  - **AJUSTADO (change streams rechazado):** exigen mantener un consumidor
    suscrito permanentemente y no aportan nada verificable en este alcance.
    Se sustituyó por evaluación del umbral **en la ingesta**: la lectura y su
    alerta se insertan juntas. Menos piezas móviles, mismo resultado.
  - **ACEPTADO (extended reference):** embeber `lastReading` y `riskLevel` en
    `patients`. La justificación es la misma que vimos en transacciones: el
    documento es la unidad de **atomicidad**, así que el snapshot se
    actualiza de forma atómica en la escritura y la vista del médico queda
    resuelta con un único `find` indexado — sin coordinar actualizaciones
    entre colecciones (el tipo de sincronización costosa, estilo two-phase
    commit, que las BD distribuidas relacionales pagan y que el modelo
    documental evita al colocar juntos los datos que se leen juntos).
  - **ACEPTADO (anti-patrón a documentar):** trasladar el esquema relacional
    normalizado a colecciones espejo con `$lookup` por consulta.
- **Validación:** revisión del esquema contra los 5 patrones (cada uno debía
  mapear a un índice concreto antes de escribir código) y confirmación
  posterior con `explain()` (ver Entrada 3). El paralelismo con el temario se
  verificó en las láminas de BD distribuidas: replicación y disponibilidad
  como ventajas, sincronización 2PC como costo — el replica set de Atlas
  materializa lo primero y el diseño de documentos minimiza lo segundo.

## Entrada 3 — Generación de código (ingesta y API)

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Prompt (resumen):** «Implementa `setup_db.py`, `seed.py` y la API según lo
  acordado. La coherencia médica no es negociable: rangos plausibles por
  sensor, anomalías correlacionadas con la condición crónica del paciente,
  fechas dentro del ciclo de vida, y alertas derivadas del umbral que definió
  el médico — nada de aleatoriedad sin sentido clínico.»
- **Respuesta:** código del pipeline (Faker con semilla fija, lotes de 10.000
  con `insert_many ordered=False`) y de la API FastAPI con middleware de
  latencias hacia la colección `metrics`.
- **Decisión: ACEPTADO CON REVISIÓN.** Se revisó el código antes de
  ejecutarlo: rangos por sensor (glucosa 45–420 mg/dL, SpO2 82–100%, etc.),
  correlación condición→sensor (diabético→glucosa, EPOC→SpO2) y que la
  alerta dependiera del umbral por paciente y no de un azar global.
- **Validación (2026-07-09):** `scripts/verify.py` tras la carga
  (`logs/verificacion.log`): 500 pacientes, 50 médicos, **200.000 lecturas
  exactas** dentro del período simulado (ene–jun 2026), 1.000 consultas,
  6.336 alertas y 245 referidos. `explain()` de la consulta del médico:
  `IXSCAN` sobre `ix_medico_estado_riesgo`, docsExamined = nReturned = 60,
  0 ms de ejecución en servidor; los 5 patrones en 60–120 ms extremo a
  extremo contra Atlas M0. La prueba funcional completa de los endpoints se
  documenta en la Entrada 5.

## Entrada 4 — Diagnóstico de conectividad al cluster

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Problema:** `pymongo` fallaba con `SSL handshake failed` contra los tres
  nodos del replica set, con la IP correctamente autorizada.
- **Prompt (resumen):** «TCP al 27017 abre pero el handshake TLS muere en los
  3 nodos; el mismo cliente hace TLS 1.3 sin problema por 443. Ayúdame a
  aislar por capas si es DNS, certificados o filtrado del túnel.»
- **Proceso (verificado paso a paso):** `Test-NetConnection` confirmó TCP
  abierto; la resolución DNS coincidió contra 8.8.8.8 (nodo legítimo de AWS);
  el handshake manual en 443 funcionó — aislando la causa: la VPN activa
  filtra TLS hacia el puerto 27017.
- **Decisión: ACEPTADO.** Ejecutar ingesta y pruebas sin la VPN activa;
  `CARGAR_DATOS.bat` automatiza carga + verificación y deja evidencia en
  `logs/`. La lista de acceso queda administrada en Atlas con autenticación
  SCRAM por usuario, de modo que el equipo completo pueda trabajar contra el
  mismo cluster.
- **Validación:** la carga y la verificación completas se ejecutaron con
  éxito inmediatamente después de desconectar el túnel, confirmando el
  diagnóstico.

## Entrada 5 — Ingesta en vivo y medición formal de KPIs

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Prompt (resumen):** «El patrón de alertas solo se ejercía dentro del seed;
  necesito exponerlo por la API para poder demostrarlo con datos nuevos, y un
  procedimiento reproducible que mida las latencias de los 5 patrones con
  parámetros variados — no una sola corrida con el mismo paciente, que
  estaría sesgada por el caché.»
- **Respuesta:** `POST /readings` (evalúa el umbral del paciente en la
  ingesta: lectura, alerta y actualización del snapshot embebido en la misma
  operación) y `scripts/measure_api.py`, que ejercita cada patrón 30 veces
  con pacientes, médicos, sensores y rangos de fechas aleatorios.
- **Decisión: ACEPTADO CON REVISIÓN.** Se verificó que el endpoint usara el
  umbral individual del paciente (no un valor global) y que la medición
  variara los parámetros en cada iteración.
- **Validación (2026-07-09):** ejecución completa contra la base poblada
  (`logs/tabla_latencias.md`): promedios extremo a extremo entre 131 y 253 ms
  (62–179 ms del lado del servidor), con P2 filtrando las 200.000 lecturas en
  ~62 ms vía el índice de la colección time series. Prueba funcional de la
  alerta: glucosa de 320 mg/dL insertada por `POST /readings` generó su
  alerta y quedó visible en `GET /alerts/active` en 274 ms. Los resultados se
  incorporaron a la sección 5 del documento técnico.

---

`[Registrar aquí las siguientes interacciones: dashboard, despliegue,
documento final.]`
