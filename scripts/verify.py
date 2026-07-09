"""Verificación post-ingesta: conteos contra los mínimos del enunciado,
consultas de los 5 patrones de acceso con tiempos, y explain() de las
consultas clave (evidencia de IXSCAN para el documento técnico)."""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import db


def timed(label, fn):
    start = time.perf_counter()
    result = fn()
    ms = (time.perf_counter() - start) * 1000
    print(f"  {label}: {ms:.1f} ms")
    return result


def main():
    print("=== Conteos (mínimos del enunciado) ===")
    expected = {"patients": 500, "doctors": 50, "vital_readings": 200_000,
                "consultations": 1_000, "alerts": 1, "referrals": 1}
    for coll, minimum in expected.items():
        n = db[coll].estimated_document_count()
        exact = db[coll].count_documents({}) if n < 10_000 else n
        flag = "OK" if exact >= minimum else "INSUFICIENTE"
        print(f"  {coll}: {exact:,}  [{flag}]")

    print("\n=== Coherencia temporal ===")
    first = db.vital_readings.find_one(sort=[("timestamp", 1)])
    last = db.vital_readings.find_one(sort=[("timestamp", -1)])
    print(f"  lecturas desde {first['timestamp']} hasta {last['timestamp']}")

    print("\n=== Patrones de acceso (latencia en frío) ===")
    pid, did = "P0001", "D001"
    timed("P1 historial (consultas+alertas de P0001)",
          lambda: (list(db.consultations.find({"patientId": pid}).sort("date", -1)),
                   list(db.alerts.find({"patientId": pid}).sort("createdAt", -1))))
    timed("P2 lecturas heart_rate de P0001 en marzo",
          lambda: list(db.vital_readings.find({
              "meta.patientId": pid, "meta.sensorType": "heart_rate",
              "timestamp": {"$gte": datetime(2026, 3, 1), "$lte": datetime(2026, 3, 31)},
          })))
    timed("P3 pacientes activos de D001 por riesgo",
          lambda: list(db.patients.find({"doctorId": did, "status": "active"})
                       .sort("riskLevel", -1)))
    timed("P4 alertas activas",
          lambda: list(db.alerts.find({"status": "active"}).sort("createdAt", -1).limit(100)))
    timed("P5 red de referidos ($graphLookup)",
          lambda: list(db.referrals.aggregate([
              {"$match": {"patientId": pid, "level": 1}},
              {"$graphLookup": {"from": "referrals", "startWith": "$toDoctorId",
                                "connectFromField": "toDoctorId",
                                "connectToField": "fromDoctorId", "as": "chain",
                                "restrictSearchWithMatch": {"patientId": pid}}},
          ])))

    print("\n=== explain() — evidencia para el documento técnico ===")
    # P3 sobre colección normal: debe mostrar IXSCAN.
    plan = db.patients.find({"doctorId": did, "status": "active"}) \
                      .sort("riskLevel", -1).explain()
    stats = plan["executionStats"]
    stage = plan["queryPlanner"]["winningPlan"]
    while "inputStage" in stage:
        stage = stage["inputStage"]
    print(f"  P3 patients: etapa={stage.get('stage')} "
          f"indice={stage.get('indexName', 'N/A')} "
          f"docsExaminados={stats['totalDocsExamined']} "
          f"devueltos={stats['nReturned']} tiempo={stats['executionTimeMillis']}ms")

    n = db.vital_readings.count_documents({
        "meta.patientId": pid, "meta.sensorType": "glucose",
        "value": {"$gt": 250},
    })
    print(f"  (spot-check) lecturas de glucosa >250 de {pid}: {n}")

    print("\nVerificación completa.")


if __name__ == "__main__":
    main()
