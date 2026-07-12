# Guía del equipo — quién necesita qué y dónde está

Mapa del repositorio por responsabilidad, para que cada quien encuentre lo
suyo sin preguntar.

## Para quien hace el DASHBOARD

- **Levantar la API en tu máquina:** sigue la "Guía rápida para el equipo" del
  [README](../README.md) — en resumen: Python instalado, descargar el repo,
  crear `.env` (pedir contenido por privado) y doble clic en `INICIAR_API.bat`.
- **Endpoints disponibles:** tabla en el README + documentación interactiva en
  `http://127.0.0.1:8000/docs` (ahí puedes probar cada uno con un clic).
- **Las 4 vistas mínimas que pide el enunciado (sección 3.4):**
  1. *Dashboard de salud del paciente* → `GET /patients/{id}/readings?sensor=...&limit=N`
     (cada lectura trae `isCritical`) + `GET /patients/{id}` (perfil completo).
  - *Tabla general de pacientes* → `GET /patients` (devuelve los 500 con
    riesgo, última lectura y condiciones, ordenados por riesgo; filtros
    opcionales `?q=nombre`, `?status=active`, `?doctorId=D001`, paginación
    con `?skip=&limit=`).
  2. *Vista del médico* (pacientes activos por riesgo) → `GET /doctors/{id}/patients`
     (ya viene ordenado por `riskLevel` descendente, con `lastReading` embebida).
  3. *Mapa de alertas activas* → `GET /alerts/active`.
  4. *Tiempo promedio de respuesta por consulta* → `GET /metrics`.
- IDs de prueba: pacientes `P0001`–`P0500`, médicos `D001`–`D050`. CORS ya
  está abierto: puedes hacer fetch desde cualquier origen, incluso un HTML
  abierto con doble clic.

## Para quien arma el DOCUMENTO TÉCNICO final

- **Base ya redactada:** [documento_tecnico.md](documento_tecnico.md) — tiene
  la justificación del motor, CAP, esquema, índices con evidencia `explain()`,
  anti-patrón, arquitectura (diagrama Mermaid: se ve renderizado en GitHub) y
  pipeline. Solo faltan los `[COMPLETAR]` marcados: tabla de latencias
  (sale de `logs/tabla_latencias.md`) y nombres/responsabilidades del equipo
  (obligatorio según notas generales del enunciado).
- **Evidencias para anexos:** `logs/verificacion.log` (conteos y explain de la
  carga) y `logs/tabla_latencias.md` (KPIs medidos).
- Exportar a PDF para el aula virtual (VS Code + extensión Markdown PDF, o
  pegar en Word).

## Para quien presenta o hace la LÁMINA

- Los 3 argumentos del motor y el CAP están en las secciones 1.2 y 1.3 del
  documento técnico — de ahí sale todo el guion.
- Números que lucen: 200.000 lecturas exactas, 6.336 alertas derivadas de
  umbrales médicos, consulta del médico resuelta con índice examinando 60
  documentos para devolver 60 (cero desperdicio), latencias en
  `logs/tabla_latencias.md`.
- Demo en vivo sugerida: `INICIAR_API.bat` → `/docs` → `POST /readings` con
  glucosa 320 → la alerta aparece en `GET /alerts/active` al instante.

## Para quien gestiona la BITÁCORA DE IA

- Ya está al día en [bitacora_ia.md](bitacora_ia.md) con el formato que exige
  el punto 4.2 (aceptado/ajustado/rechazado + validación técnica). Si alguien
  del equipo usa IA para el dashboard o las láminas, debe agregar su entrada
  con el mismo formato.

## Base de datos (ya lista, no hay que hacer nada)

- La base vive en MongoDB Atlas (nube) y **ya está poblada**: 500 pacientes,
  50 médicos, 200.000 lecturas, 1.000 consultas, alertas y referidos.
- Si alguna vez hace falta recargarla desde cero: `CARGAR_DATOS.bat`
  (destruye y regenera todo, tarda unos minutos).
- El esquema y los índices están en `scripts/setup_db.py`; la generación de
  datos en `scripts/seed.py`; la verificación en `scripts/verify.py`.
