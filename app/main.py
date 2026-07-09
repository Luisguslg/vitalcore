"""API REST de VitalCore.

Cada endpoint implementa uno de los patrones de acceso críticos del
enunciado. Un middleware mide la latencia de cada request y la persiste
en la colección `metrics`, que alimenta el KPI de tiempo promedio de
respuesta por consulta.
"""
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from app.db import db

app = FastAPI(
    title="VitalCore API",
    description="Arquitectura de datos en tiempo real para salud digital (MongoDB)",
    version="1.0.0",
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

MEASURED_PREFIXES = ("/patients", "/doctors", "/alerts")


@app.middleware("http")
async def measure_latency(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - start) * 1000
    response.headers["X-Response-Time-ms"] = f"{ms:.2f}"
    if request.url.path.startswith(MEASURED_PREFIXES):
        route = request.scope.get("route")
        db.metrics.insert_one({
            "endpoint": route.path if route else request.url.path,
            "method": request.method,
            "ms": round(ms, 2),
            "at": datetime.utcnow(),
        })
    return response


def parse_date(value: Optional[str], field: str) -> Optional[datetime]:
    if value is None:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(422, f"'{field}' debe ser fecha ISO, ej. 2026-03-15")


# ── Patrón 1: historial clínico completo, ordenado cronológicamente ──────────
@app.get("/patients/{patient_id}/history", tags=["patrones de acceso"])
def patient_history(patient_id: str):
    patient = db.patients.find_one({"_id": patient_id})
    if not patient:
        raise HTTPException(404, "Paciente no encontrado")
    consultations = list(db.consultations.find(
        {"patientId": patient_id}, {"patientId": 0}).sort("date", -1))
    alerts = list(db.alerts.find(
        {"patientId": patient_id}, {"patientId": 0}).sort("createdAt", -1))
    events = (
        [{"type": "consultation", "date": c.pop("date"), **_clean(c)} for c in consultations]
        + [{"type": "alert", "date": a.pop("createdAt"), **_clean(a)} for a in alerts]
    )
    events.sort(key=lambda e: e["date"], reverse=True)
    return {"patient": patient, "events": events}


# ── Patrón 2: lecturas de un sensor en un rango de fechas ────────────────────
@app.get("/patients/{patient_id}/readings", tags=["patrones de acceso"])
def patient_readings(
    patient_id: str,
    sensor: str = Query(..., description="ej. glucose, heart_rate, spo2"),
    date_from: Optional[str] = Query(None, alias="from"),
    date_to: Optional[str] = Query(None, alias="to"),
    limit: int = Query(500, le=5000),
):
    query = {"meta.patientId": patient_id, "meta.sensorType": sensor}
    time_filter = {}
    if (df := parse_date(date_from, "from")):
        time_filter["$gte"] = df
    if (dt := parse_date(date_to, "to")):
        time_filter["$lte"] = dt
    if time_filter:
        query["timestamp"] = time_filter
    readings = list(db.vital_readings.find(query, {"_id": 0, "meta": 0})
                    .sort("timestamp", -1).limit(limit))
    return {"patientId": patient_id, "sensor": sensor, "count": len(readings),
            "readings": readings}


# ── Patrón 3: pacientes activos de un médico con su última lectura ───────────
# Un solo find indexado gracias al extended reference (lastReading/riskLevel
# embebidos en el paciente); no se agrega sobre las 200k lecturas.
@app.get("/doctors/{doctor_id}/patients", tags=["patrones de acceso"])
def doctor_patients(doctor_id: str):
    doctor = db.doctors.find_one({"_id": doctor_id})
    if not doctor:
        raise HTTPException(404, "Médico no encontrado")
    patients = list(db.patients.find(
        {"doctorId": doctor_id, "status": "active"},
        {"name": 1, "conditions": 1, "lastReading": 1, "riskLevel": 1, "riskLabel": 1},
    ).sort("riskLevel", -1))
    return {"doctor": doctor, "activePatients": len(patients), "patients": patients}


# ── Patrón 4: alertas activas (mapa de eventos críticos sin resolver) ────────
@app.get("/alerts/active", tags=["patrones de acceso"])
def active_alerts(limit: int = Query(100, le=1000)):
    alerts = list(db.alerts.find({"status": "active"}).sort("createdAt", -1).limit(limit))
    return {"count": len(alerts), "alerts": [_clean(a) for a in alerts]}


# ── Patrón 5: red de referidos del paciente ($graphLookup) ───────────────────
@app.get("/patients/{patient_id}/referrals", tags=["patrones de acceso"])
def referral_network(patient_id: str):
    pipeline = [
        {"$match": {"patientId": patient_id, "level": 1}},
        {"$graphLookup": {
            "from": "referrals",
            "startWith": "$toDoctorId",
            "connectFromField": "toDoctorId",
            "connectToField": "fromDoctorId",
            "as": "chain",
            "restrictSearchWithMatch": {"patientId": patient_id},
        }},
    ]
    roots = list(db.referrals.aggregate(pipeline))
    if not roots:
        return {"patientId": patient_id, "network": [], "doctors": {}}
    edges = []
    for root in roots:
        chain = root.pop("chain")
        edges.append(_clean(root))
        edges.extend(_clean(c) for c in chain)
    seen, network = set(), []
    for e in edges:
        key = (e["fromDoctorId"], e["toDoctorId"], e["level"])
        if key not in seen:
            seen.add(key)
            network.append(e)
    network.sort(key=lambda e: e["level"])
    ids = {e["fromDoctorId"] for e in network} | {e["toDoctorId"] for e in network}
    doctors = {d["_id"]: {"name": d["name"], "specialty": d["specialty"]}
               for d in db.doctors.find({"_id": {"$in": list(ids)}})}
    return {"patientId": patient_id, "network": network, "doctors": doctors}


# ── KPI: tiempo promedio de respuesta por consulta ───────────────────────────
@app.get("/metrics", tags=["kpis"])
def metrics():
    pipeline = [
        {"$group": {
            "_id": {"endpoint": "$endpoint", "method": "$method"},
            "avgMs": {"$avg": "$ms"},
            "p95Ms": {"$percentile": {"input": "$ms", "p": [0.95], "method": "approximate"}},
            "count": {"$sum": 1},
        }},
        {"$sort": {"avgMs": -1}},
    ]
    try:
        rows = list(db.metrics.aggregate(pipeline))
    except Exception:
        # $percentile requiere MongoDB 7+; fallback sin p95.
        rows = list(db.metrics.aggregate([
            {"$group": {"_id": {"endpoint": "$endpoint", "method": "$method"},
                        "avgMs": {"$avg": "$ms"}, "count": {"$sum": 1}}},
            {"$sort": {"avgMs": -1}},
        ]))
    return {"queries": [
        {"endpoint": r["_id"]["endpoint"], "method": r["_id"]["method"],
         "avgMs": round(r["avgMs"], 2),
         "p95Ms": round(r["p95Ms"][0], 2) if isinstance(r.get("p95Ms"), list) else None,
         "requests": r["count"]}
        for r in rows
    ]}


# ── Auxiliares para el dashboard ─────────────────────────────────────────────
@app.get("/patients", tags=["auxiliares"])
def list_patients(q: Optional[str] = None, limit: int = Query(20, le=100)):
    query = {"name": {"$regex": q, "$options": "i"}} if q else {}
    return list(db.patients.find(query, {"name": 1, "status": 1, "riskLabel": 1}).limit(limit))


@app.get("/doctors", tags=["auxiliares"])
def list_doctors(specialty: Optional[str] = None):
    query = {"specialty": specialty} if specialty else {}
    return list(db.doctors.find(query, {"name": 1, "specialty": 1}))


@app.get("/health", tags=["auxiliares"])
def health():
    db.command("ping")
    return {"status": "ok", "database": db.name}


def _clean(doc: dict) -> dict:
    """Serializa ObjectId a str para las colecciones sin _id propio."""
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc
