# Bitácora de Auditoría de Prompts — VitalCore

Formato por entrada: herramienta, prompt (resumen), respuesta relevante,
**decisión** (aceptado / ajustado / rechazado) y **validación técnica**
(cómo comprobamos que era correcto).

---

## Entrada 1 — Selección del motor NoSQL

- **Fecha:** 2026-07-09 · **Herramienta:** OpenAI Codex (GPT-5.5)
- **Prompt:** «Dime qué manejador usar, o cuáles 2 son los mejores para este
  proyecto» (adjuntando el enunciado del PDF).
- **Respuesta:** recomendó MongoDB como motor principal y Cassandra/ScyllaDB
  como alternativa a comparar; citó documentación oficial de time series
  collections, réplica y CAP.
- **Decisión: ACEPTADO.** La recomendación coincide con el análisis propio de
  los patrones de acceso (4 de 5 patrones son centrados en documentos).
- **Validación:** contrastamos las capacidades citadas contra la documentación
  oficial de MongoDB (time series collections, `$graphLookup`, write/read
  concern majority) y verificamos que cada patrón del enunciado tiene una
  estrategia concreta en el motor elegido antes de fijar la decisión.

## Entrada 2 — Lineamientos de arquitectura y ajustes al diseño

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Prompt:** solicitud de lineamientos completos del proyecto, con el
  enunciado y el resumen de la conversación previa con Codex.
- **Respuesta:** plan en 6 pasos (esquema → ingesta → API → dashboard → docs →
  bitácora) y andamiaje del repositorio.
- **Decisiones:**
  - **ACEPTADO:** MongoDB único con comparación formal contra Cassandra;
    colección time series para telemetría; `$graphLookup` para referidos.
  - **AJUSTADO (propuesta de Codex rechazada parcialmente):** Codex sugería
    *change streams* para las alertas en tiempo real. Se sustituyó por
    **generación de alertas en la ingesta** (al insertar una lectura que supera
    el umbral del paciente se inserta la alerta): mismo resultado observable,
    sin exigir infraestructura adicional ni lógica de suscripción.
  - **ACEPTADO (mejora sobre el diseño inicial):** patrón *extended reference*
    — embeber `lastReading` y `riskLevel` en `patients` para que la vista del
    médico sea un solo `find` indexado en lugar de agregar sobre 200k lecturas.
- **Validación:** `[COMPLETAR tras poblar: explain() de P3 mostrando IXSCAN
  sobre ix_medico_estado_riesgo y latencia medida en /metrics; conteos de
  colecciones contra los mínimos del enunciado con db.collection.countDocuments()]`

## Entrada 3 — Generación de código (scripts de ingesta y API)

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Prompt:** implementación de `setup_db.py`, `seed.py` y `app/main.py`
  conforme a los lineamientos acordados.
- **Respuesta:** código completo del pipeline y la API.
- **Decisión: ACEPTADO CON REVISIÓN.** El código se revisó línea a línea antes
  de ejecutarlo; se verificó que los rangos de sensores fueran médicamente
  plausibles y que las alertas dependieran del umbral por paciente y no de
  aleatoriedad pura.
- **Validación (2026-07-09):** se ejecutó `scripts/verify.py` tras la carga
  (`logs/verificacion.log`): 500 pacientes, 50 médicos, 200.000 lecturas
  exactas dentro del rango simulado (ene–jun 2026), 1.000 consultas, 6.336
  alertas y 245 referidos. `explain()` de la consulta del médico confirmó
  `IXSCAN` sobre `ix_medico_estado_riesgo` con docsExamined = nReturned = 60
  y 0 ms en servidor; los 5 patrones respondieron en 60–120 ms extremo a
  extremo contra Atlas M0. Pendiente: prueba interactiva de los endpoints
  en /docs al levantar la API.

## Entrada 4 — Diagnóstico de conectividad a Atlas (bloqueo de VPN)

- **Fecha:** 2026-07-09 · **Herramienta:** Claude Code (Fable 5)
- **Problema:** `pymongo` fallaba con `SSL handshake failed` contra los 3
  nodos del replica set, pese a que la IP estaba en la lista de acceso.
- **Proceso de diagnóstico guiado por la IA (verificado paso a paso):**
  TCP al puerto 27017 conectaba (`Test-NetConnection`), el DNS resolvía al
  nodo legítimo de AWS (contrastado contra 8.8.8.8), y el TLS de Python
  funcionaba en el puerto 443 — aislando la causa: la VPN (Proton Free)
  corta TLS hacia el puerto 27017 en todos sus servidores.
- **Decisión: ACEPTADO.** Solución adoptada: ejecutar ingesta y pruebas de la
  API sin VPN (`CARGAR_DATOS.bat` automatiza carga + verificación y deja
  evidencia en `logs/`), manteniendo la lista de acceso abierta con
  autenticación por usuario/contraseña para el trabajo del equipo.
- **Validación:** la carga completa y la verificación se ejecutaron con éxito
  inmediatamente después de desconectar la VPN, confirmando el diagnóstico.

---

`[Agregar aquí cada interacción nueva con IA durante el resto del proyecto:
dashboard, documento técnico, correcciones.]`
