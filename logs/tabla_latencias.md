# Reporte de latencias — VitalCore API

Iteraciones por consulta: 30. Cliente y servidor en la misma máquina; la latencia incluye el viaje de red hasta MongoDB Atlas (region US East).

| Patrón / Consulta | Promedio (ms) | p95 (ms) | Mín (ms) | Máx (ms) |
|---|---|---|---|---|
| P1 GET /patients/{id}/history | 253.2 | 263.7 | 241.0 | 270.8 |
| P2 GET /patients/{id}/readings (sensor+rango) | 131.2 | 139.5 | 124.0 | 146.5 |
| P3 GET /doctors/{id}/patients | 195.1 | 202.1 | 186.4 | 210.3 |
| P4 GET /alerts/active | 139.9 | 145.8 | 128.8 | 146.0 |
| P5 GET /patients/{id}/referrals | 139.5 | 187.5 | 123.0 | 216.0 |

**Alerta por umbral (POST /readings):** lectura crítica insertada y alerta visible en /alerts/active en 274.2 ms (paciente P0204, glucosa 320 mg/dL, alertId 6a4fd41d264902925f6a02c0).

## Vista del servidor (colección metrics, GET /metrics)

| Endpoint | Método | Promedio (ms) | p95 (ms) | Requests |
|---|---|---|---|---|
| /patients/{patient_id}/history | GET | 179.35 | 187.79 | 30 |
| /doctors/{doctor_id}/patients | GET | 122.34 | 124.57 | 30 |
| /patients/{patient_id}/referrals | GET | 68.29 | 120.69 | 30 |
| /alerts/active | GET | 66.2 | 67.0 | 31 |
| /doctors | GET | 65.79 | 65.79 | 1 |
| /patients/{patient_id}/readings | GET | 62.01 | 64.1 | 30 |
