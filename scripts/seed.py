"""Pipeline de ingesta de VitalCore: genera y carga datos sintéticos
con coherencia médica (rangos plausibles, fechas dentro del ciclo de
vida del paciente, alertas derivadas de umbrales definidos por el médico).

Volumen (mínimos del enunciado):
  - 50 médicos en 6 especialidades
  - 500 pacientes con perfiles heterogéneos
  - 200.000 lecturas de telemetría en 6 meses simulados (ene–jun 2026)
  - 1.000 consultas médicas con notas de longitud variable
  - Alertas y red de referidos derivadas de la lógica anterior
"""
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from faker import Faker

from app.db import db
from scripts.setup_db import create_collections, create_indexes

fake = Faker("es_ES")
random.seed(42)
Faker.seed(42)

SIM_START = datetime(2026, 1, 1)
SIM_END = datetime(2026, 6, 30, 23, 59)
SIM_SECONDS = int((SIM_END - SIM_START).total_seconds())

N_DOCTORS = 50
N_PATIENTS = 500
N_READINGS = 200_000
N_CONSULTATIONS = 1_000

SPECIALTIES = [
    "Medicina General", "Cardiología", "Endocrinología",
    "Neumonología", "Nefrología", "Neurología",
]

# Rangos médicamente plausibles por sensor y umbrales que define el médico.
SENSORS = {
    "heart_rate": {"unit": "bpm", "normal": (58, 100), "critical_low": (38, 49), "critical_high": (146, 185),
                   "threshold": {"min": 50, "max": 145}},
    "glucose": {"unit": "mg/dL", "normal": (72, 140), "critical_low": (45, 60), "critical_high": (251, 420),
                "threshold": {"min": 62, "max": 250}},
    "spo2": {"unit": "%", "normal": (95, 100), "critical_low": (82, 89), "critical_high": None,
             "threshold": {"min": 90, "max": None}},
    "blood_pressure_systolic": {"unit": "mmHg", "normal": (98, 132), "critical_low": (78, 89), "critical_high": (181, 215),
                                "threshold": {"min": 90, "max": 180}},
    "body_temperature": {"unit": "°C", "normal": (35.9, 37.2), "critical_low": None, "critical_high": (39.1, 40.6),
                         "threshold": {"min": 35.0, "max": 39.0}},
}

# Condiciones crónicas y el sensor cuya anomalía es coherente con cada una.
CONDITIONS = {
    "diabetes tipo 2": "glucose",
    "hipertensión arterial": "blood_pressure_systolic",
    "arritmia cardíaca": "heart_rate",
    "EPOC": "spo2",
    "asma": "spo2",
    "insuficiencia renal crónica": "blood_pressure_systolic",
    "hipotiroidismo": "heart_rate",
    "obesidad": "glucose",
}

WEARABLES = ["Fitbit Charge 6", "Apple Watch S10", "Garmin Venu 3", "Xiaomi Band 9", "Dexcom G7"]


def sim_datetime(start=SIM_START, end=SIM_END):
    delta = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, delta))


def seed_doctors():
    docs = []
    for i in range(N_DOCTORS):
        # Garantiza cobertura de las 6 especialidades; ~1/3 son generales
        # para que existan médicos tratantes que originen referidos.
        specialty = SPECIALTIES[i % len(SPECIALTIES)] if i < 18 else random.choice(SPECIALTIES)
        docs.append({
            "_id": f"D{i + 1:03d}",
            "name": f"Dr(a). {fake.name()}",
            "specialty": specialty,
            "licenseNumber": f"MPPS-{random.randint(10000, 99999)}",
            "email": fake.unique.email(),
            "yearsOfExperience": random.randint(2, 35),
        })
    db.doctors.insert_many(docs)
    return docs


def seed_patients(doctors):
    general = [d for d in doctors if d["specialty"] == "Medicina General"]
    patients = []
    for i in range(N_PATIENTS):
        birth = fake.date_of_birth(minimum_age=18, maximum_age=90)
        n_cond = random.choices([0, 1, 2, 3], weights=[30, 40, 22, 8])[0]
        conditions = random.sample(list(CONDITIONS), n_cond)
        # Umbrales definidos por el médico, con ajuste individual leve.
        thresholds = {}
        for sensor, cfg in SENSORS.items():
            t = dict(cfg["threshold"])
            if t.get("max") and random.random() < 0.3:
                t["max"] = round(t["max"] * random.uniform(0.95, 1.05))
            thresholds[sensor] = t

        p = {
            "_id": f"P{i + 1:04d}",
            "name": fake.name(),
            "birthDate": datetime(birth.year, birth.month, birth.day),
            "gender": random.choice(["F", "M"]),
            "bloodType": random.choice(["O+", "O-", "A+", "A-", "B+", "B-", "AB+", "AB-"]),
            "status": "active" if random.random() < 0.85 else "inactive",
            "doctorId": random.choice(general)["_id"],
            "conditions": conditions,
            "thresholds": thresholds,
            # Se actualiza durante la ingesta de lecturas (extended reference).
            "lastReading": None,
            "riskLevel": 0,
            "enrolledAt": sim_datetime(SIM_START - timedelta(days=365), SIM_START),
        }
        # Heterogeneidad real: no todos los documentos tienen los mismos campos.
        if random.random() < 0.55:
            p["devices"] = random.sample(WEARABLES, random.randint(1, 2))
        if random.random() < 0.35:
            p["allergies"] = random.sample(
                ["penicilina", "aspirina", "sulfas", "látex", "mariscos", "maní"],
                random.randint(1, 2))
        if random.random() < 0.6:
            p["emergencyContact"] = {"name": fake.name(), "phone": fake.phone_number()}
        patients.append(p)
    db.patients.insert_many(patients)
    return patients


def seed_readings(patients):
    """Genera N_READINGS distribuidas de forma no uniforme: los pacientes
    crónicos monitorean más y sus anomalías son coherentes con su condición."""
    weights = [1 + 2 * len(p["conditions"]) + (1 if "devices" in p else 0) for p in patients]
    total_w = sum(weights)
    counts = [max(20, round(N_READINGS * w / total_w)) for w in weights]
    # Reparte la diferencia para clavar el total exacto sin bajar de 20.
    diff = N_READINGS - sum(counts)
    i = 0
    while diff != 0:
        step = 1 if diff > 0 else -1
        if step > 0 or counts[i % len(counts)] > 20:
            counts[i % len(counts)] += step
            diff -= step
        i += 1

    critical_by_patient = {}
    last_by_patient = {}
    batch, inserted = [], 0
    for p, n in zip(patients, counts):
        sensors = ["heart_rate"]  # todo wearable mide pulso
        sensors += [CONDITIONS[c] for c in p["conditions"]]
        sensors += random.sample([s for s in SENSORS if s not in sensors],
                                 k=min(2, 5 - len(set(sensors))))
        sensors = list(set(sensors))
        # Probabilidad de lectura anómala crece con las condiciones crónicas.
        p_crit = 0.01 + 0.015 * len(p["conditions"])

        for _ in range(n):
            sensor = random.choice(sensors)
            cfg = SENSORS[sensor]
            is_crit = random.random() < p_crit and (cfg["critical_low"] or cfg["critical_high"])
            if is_crit:
                side = random.choice([r for r in (cfg["critical_low"], cfg["critical_high"]) if r])
                value = round(random.uniform(*side), 1)
            else:
                value = round(random.uniform(*cfg["normal"]), 1)
            ts = sim_datetime(max(SIM_START, p["enrolledAt"]), SIM_END)
            reading = {
                "timestamp": ts,
                "meta": {"patientId": p["_id"], "sensorType": sensor},
                "value": value,
                "unit": cfg["unit"],
                "isCritical": bool(is_crit),
            }
            batch.append(reading)
            if is_crit:
                critical_by_patient.setdefault(p["_id"], []).append(reading)
            prev = last_by_patient.get(p["_id"])
            if prev is None or ts > prev["timestamp"]:
                last_by_patient[p["_id"]] = reading
            if len(batch) >= 10_000:
                db.vital_readings.insert_many(batch, ordered=False)
                inserted += len(batch)
                print(f"  lecturas insertadas: {inserted:,}")
                batch = []
    if batch:
        db.vital_readings.insert_many(batch, ordered=False)
        inserted += len(batch)
    print(f"  total lecturas: {inserted:,}")
    return critical_by_patient, last_by_patient


def seed_alerts(patients, critical_by_patient):
    """Cada lectura crítica que supera el umbral definido por el médico
    genera una alerta; la mayoría ya fue atendida, una parte sigue activa."""
    by_id = {p["_id"]: p for p in patients}
    alerts = []
    for pid, readings in critical_by_patient.items():
        p = by_id[pid]
        for r in readings:
            t = p["thresholds"][r["meta"]["sensorType"]]
            breached = (t.get("max") and r["value"] > t["max"]) or \
                       (t.get("min") and r["value"] < t["min"])
            if not breached:
                continue
            age_days = (SIM_END - r["timestamp"]).days
            status = "active" if age_days < 10 and random.random() < 0.6 else \
                     random.choice(["acknowledged", "resolved", "resolved"])
            alerts.append({
                "patientId": pid,
                "doctorId": p["doctorId"],
                "sensorType": r["meta"]["sensorType"],
                "value": r["value"],
                "unit": r["unit"],
                "threshold": t,
                "severity": "high" if random.random() < 0.35 else "medium",
                "status": status,
                "createdAt": r["timestamp"],
                "resolvedAt": r["timestamp"] + timedelta(hours=random.randint(1, 48))
                              if status == "resolved" else None,
            })
    if alerts:
        db.alerts.insert_many(alerts)
    print(f"  alertas generadas: {len(alerts):,}")


def update_patient_snapshots(patients, critical_by_patient, last_by_patient):
    """Extended reference: embebe la última lectura y calcula el nivel de
    riesgo en el documento del paciente para que la vista del médico sea
    un único find indexado (sin agregar sobre 200k lecturas)."""
    recent_cut = SIM_END - timedelta(days=30)
    for p in patients:
        last = last_by_patient.get(p["_id"])
        recent_crit = sum(1 for r in critical_by_patient.get(p["_id"], [])
                          if r["timestamp"] >= recent_cut)
        risk = 3 if recent_crit >= 5 else 2 if recent_crit >= 2 else 1 if recent_crit == 1 else 0
        db.patients.update_one({"_id": p["_id"]}, {"$set": {
            "riskLevel": risk,
            "riskLabel": ["bajo", "moderado", "alto", "crítico"][risk],
            "lastReading": {
                "sensorType": last["meta"]["sensorType"],
                "value": last["value"],
                "unit": last["unit"],
                "timestamp": last["timestamp"],
                "isCritical": last["isCritical"],
            } if last else None,
        }})
    print("  snapshots de riesgo/última lectura actualizados.")


def seed_consultations(patients, doctors):
    reasons = ["control de rutina", "seguimiento de condición crónica", "dolor torácico",
               "mareos y fatiga", "ajuste de medicación", "resultados de laboratorio",
               "disnea de esfuerzo", "cefalea persistente"]
    docs = []
    for _ in range(N_CONSULTATIONS):
        p = random.choice(patients)
        docs.append({
            "patientId": p["_id"],
            "doctorId": random.choice([p["doctorId"], random.choice(doctors)["_id"]]),
            "date": sim_datetime(max(SIM_START, p["enrolledAt"]), SIM_END),
            "reason": random.choice(reasons),
            "notes": "\n\n".join(fake.paragraphs(nb=random.randint(1, 5))),
            "diagnosis": random.choice(list(CONDITIONS) + ["sin hallazgos relevantes"]),
            "prescriptions": [fake.word() + " " + random.choice(["500mg", "50mg", "10mg"])
                              for _ in range(random.randint(0, 3))] or None,
        })
    db.consultations.insert_many(docs)
    print(f"  consultas generadas: {len(docs):,}")


def seed_referrals(patients, doctors):
    """Cadenas médico general → especialista(s) para ~40% de los pacientes
    crónicos; se recorren en la API con $graphLookup."""
    specialists = [d for d in doctors if d["specialty"] != "Medicina General"]
    docs = []
    for p in patients:
        if not p["conditions"] or random.random() > 0.4:
            continue
        current = p["doctorId"]
        date = sim_datetime()
        for level in range(1, random.randint(2, 4)):
            target = random.choice(specialists)["_id"]
            docs.append({
                "patientId": p["_id"],
                "fromDoctorId": current,
                "toDoctorId": target,
                "level": level,
                "reason": f"evaluación por {random.choice(p['conditions'])}",
                "date": date,
            })
            current = target
            date = min(date + timedelta(days=random.randint(3, 30)), SIM_END)
    if docs:
        db.referrals.insert_many(docs)
    print(f"  referidos generados: {len(docs):,}")


def main():
    print("Limpiando colecciones previas…")
    for name in ["patients", "doctors", "vital_readings", "consultations",
                 "alerts", "referrals", "metrics"]:
        db.drop_collection(name)

    create_collections()
    print("Insertando médicos…")
    doctors = seed_doctors()
    print("Insertando pacientes…")
    patients = seed_patients(doctors)
    print("Insertando lecturas de telemetría…")
    critical, last = seed_readings(patients)
    print("Generando alertas por umbral…")
    seed_alerts(patients, critical)
    update_patient_snapshots(patients, critical, last)
    print("Insertando consultas médicas…")
    seed_consultations(patients, doctors)
    print("Insertando referidos…")
    seed_referrals(patients, doctors)
    create_indexes()
    print("\nIngesta completa.")


if __name__ == "__main__":
    main()
