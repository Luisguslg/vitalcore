# VitalCore — NoSQL Implementation Challenge (Proyecto 02)

Arquitectura de datos operativa sobre **MongoDB Atlas** para una plataforma de
salud digital: ingesta de datos sintéticos con coherencia médica, API REST con
los patrones de acceso críticos y KPIs de latencia medidos.

## Requisitos

- Python 3.10+
- Cuenta gratuita en [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)

## 1. Crear el cluster en Atlas (una sola vez, lo comparte el equipo)

1. Regístrate en Atlas y crea un cluster **M0 (gratis)** — región más cercana.
2. En **Database Access** crea un usuario con contraseña (rol `readWriteAnyDatabase`).
3. En **Network Access** agrega `0.0.0.0/0` (acceso desde cualquier IP; suficiente
   para un proyecto académico).
4. En **Connect → Drivers** copia el connection string
   (`mongodb+srv://usuario:password@cluster...`).

## 2. Configurar el entorno

```powershell
cd vitalcore
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # y edita .env con tu connection string
```

## 3. Poblar la base de datos

```powershell
python scripts\seed.py
```

Genera y carga: 50 médicos (6 especialidades), 500 pacientes heterogéneos,
200.000 lecturas de telemetría (ene–jun 2026), ~1.000 consultas, alertas
derivadas de umbrales médicos y cadenas de referidos. Crea la colección
time series y todos los índices. Tarda ~2–5 min contra Atlas M0.

## 4. Levantar la API

```powershell
uvicorn app.main:app --reload
```

Documentación interactiva (sirve de demo): http://127.0.0.1:8000/docs

## Endpoints (patrones de acceso del enunciado)

| Patrón | Endpoint |
|---|---|
| Historial clínico cronológico | `GET /patients/{id}/history` |
| Lecturas de un sensor por rango de fechas | `GET /patients/{id}/readings?sensor=glucose&from=2026-03-01&to=2026-03-31` |
| Pacientes activos de un médico por riesgo | `GET /doctors/{id}/patients` |
| Alertas activas (eventos críticos sin resolver) | `GET /alerts/active` |
| Red de referidos (`$graphLookup`) | `GET /patients/{id}/referrals` |
| Ingesta de lectura con alerta por umbral en vivo | `POST /readings` |
| KPI: latencia promedio y p95 por consulta | `GET /metrics` |

Para medir y reportar los KPIs de latencia: `PROBAR_API.bat` (ejercita cada
patrón 30 veces y genera `logs/tabla_latencias.md`).

IDs de ejemplo: pacientes `P0001`…`P0500`, médicos `D001`…`D050`.
Toda respuesta incluye el header `X-Response-Time-ms`.

## Inicio rápido (cualquier máquina Windows)

1. Instala [Python 3.10+](https://www.python.org/downloads/) marcando
   **"Add Python to PATH"** durante la instalación.
2. Clona o descarga el repositorio
   (`git clone https://github.com/Luisguslg/vitalcore.git`).
3. Crea el archivo `.env` en la raíz del proyecto con las credenciales de
   conexión a Atlas, usando `.env.example` como plantilla.
4. Doble clic en **`INICIAR_API.bat`** — la primera vez instala las
   dependencias (1–2 min) y luego levanta el servidor. La documentación
   interactiva queda en http://127.0.0.1:8000/docs.
5. La base de datos ya está poblada en Atlas; para regenerarla desde cero,
   ejecutar `CARGAR_DATOS.bat`.

## Interfaz de visualización

El dashboard del proyecto está desarrollado en **Power BI**
(`vitalcore_dashboard.pbix`, entregado junto al informe) y consume esta API:
vistas de pacientes por nivel de riesgo, doctores por especialidad y KPIs de
rendimiento por endpoint. La API expone CORS abierto, por lo que cualquier
otro cliente de visualización puede consumirla directamente.

## Estructura

```
vitalcore/
├── app/            # API FastAPI (main.py) y conexión (db.py)
├── scripts/        # setup_db.py (índices), seed.py (ingesta), verify.py,
│                   # measure_api.py (medición de KPIs)
├── docs/           # documento técnico, bitácora de IA y diccionario de datos
└── logs/           # evidencias: verificación de carga y tabla de latencias
```
