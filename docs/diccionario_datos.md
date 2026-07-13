# Diccionario de datos — VitalCore

Referencia de las colecciones de MongoDB y sus campos, en lenguaje llano,
para quien consume la API o revisa el modelo. Regla general de relaciones:
**todo se vincula por `patientId` → `patients._id` (ej. "P0204") y
`doctorId` → `doctors._id` (ej. "D001")**; no existen otras claves foráneas.

## patients — pacientes (500)

| Campo | Qué es |
|---|---|
| `_id` | Código del paciente: "P0001" … "P0500" |
| `name`, `birthDate`, `gender`, `bloodType` | Identificación básica (F/M; tipo de sangre) |
| `status` | "active" o "inactive" |
| `doctorId` | Médico tratante (medicina general) → `doctors` |
| `conditions` | Condiciones crónicas: "diabetes tipo 2", "EPOC", etc. Puede estar vacía |
| `thresholds` | Umbrales de alerta por sensor definidos por el médico: `{glucose: {min, max}, …}` |
| `lastReading` | **Embebido**: última medición (sensor, valor, unidad, hora, `isCritical`) — evita consultar las 200k lecturas para la vista del médico |
| `riskLevel` / `riskLabel` | Riesgo precalculado: 0–3 / "bajo", "moderado", "alto", "crítico" |
| `enrolledAt` | Fecha de inscripción en la plataforma |
| `devices`, `allergies`, `emergencyContact` | **Opcionales** (heterogeneidad real del modelo documental): wearables, alergias, contacto de emergencia |

## doctors — médicos (50)

`_id` ("D001"…"D050"), `name`, `specialty` (6 especialidades),
`licenseNumber`, `email`, `yearsOfExperience`.

## vital_readings — telemetría (200.000, colección time series)

| Campo | Qué es |
|---|---|
| `timestamp` | Fecha/hora de la medición (ene–jun 2026) |
| `meta.patientId` / `meta.sensorType` | Paciente y sensor (metadatos del bucket de la serie de tiempo) |
| `value`, `unit` | Valor medido y su unidad |
| `isCritical` | `true` si el valor está en rango peligroso |

Sensores: `heart_rate` (bpm), `glucose` (mg/dL), `spo2` (%),
`blood_pressure_systolic` (mmHg), `body_temperature` (°C).

## alerts — alertas por umbral (~6.300)

`patientId`, `doctorId`, `sensorType`, `value`, `unit`,
`threshold` (el umbral violado), `severity` ("high"/"medium"),
`status` ("active" = sin resolver, "acknowledged", "resolved"),
`createdAt`, `resolvedAt` (null si sigue activa).

## consultations — consultas médicas (1.000)

`patientId`, `doctorId`, `date`, `reason` (motivo), `notes` (nota clínica de
longitud variable), `diagnosis`, `prescriptions` (lista, puede ser null).

## referrals — referidos (aristas del grafo, 245)

`patientId`, `fromDoctorId` → `toDoctorId` (quién refirió a quién),
`level` (1 = del médico general, 2–3 = saltos entre especialistas),
`reason`, `date`. Se recorre con `$graphLookup` en
`GET /patients/{id}/referrals`, que además devuelve los nombres de los
médicos involucrados.

## metrics — telemetría de la propia API

`endpoint`, `method`, `ms` (duración del request), `at`. Alimenta el KPI de
`GET /metrics`.

## Notas para el consumo desde el dashboard

- Las fechas llegan en formato ISO (`"2026-03-15T10:22:00"`):
  `new Date(f).toLocaleString("es-VE")` en JavaScript.
- Los campos opcionales de `patients` pueden no venir: usar `campo ?? "—"`.
- `riskLabel` ya viene calculado — mapear directo a colores
  (bajo=verde, moderado=amarillo, alto=naranja, crítico=rojo).
- Etiquetas sugeridas para sensores: heart_rate = "Frecuencia cardíaca",
  glucose = "Glucosa", spo2 = "Oxígeno (SpO2)",
  blood_pressure_systolic = "Presión sistólica",
  body_temperature = "Temperatura".
