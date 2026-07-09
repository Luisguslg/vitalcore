"""Crea las colecciones (incluida la de series de tiempo) y los índices.

Cada índice responde a un patrón de acceso concreto del enunciado;
ver docs/documento_tecnico.md sección "Estrategia de indexación".
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import CollectionInvalid, OperationFailure

from app.db import db


def create_collections():
    # vital_readings como time series: almacenamiento columnar por buckets,
    # optimizado para inserciones masivas y consultas por rango de tiempo.
    try:
        db.create_collection(
            "vital_readings",
            timeseries={
                "timeField": "timestamp",
                "metaField": "meta",
                "granularity": "minutes",
            },
        )
        print("Colección time series 'vital_readings' creada.")
    except CollectionInvalid:
        print("'vital_readings' ya existe, se omite.")
    except OperationFailure as exc:
        # Fallback documentado: si el tier no soporta time series se usa
        # una colección normal con los mismos índices (patrón bucket manual
        # queda como mejora futura).
        print(f"Time series no soportado ({exc.details.get('errmsg', exc)}); "
              "se usará una colección estándar.")


def create_indexes():
    # Patrón: lecturas de un sensor de un paciente en un rango de fechas.
    db.vital_readings.create_index(
        [("meta.patientId", ASCENDING), ("meta.sensorType", ASCENDING), ("timestamp", DESCENDING)],
        name="ix_paciente_sensor_tiempo",
    )
    # Patrón: pacientes activos de un médico ordenados por riesgo.
    db.patients.create_index(
        [("doctorId", ASCENDING), ("status", ASCENDING), ("riskLevel", DESCENDING)],
        name="ix_medico_estado_riesgo",
    )
    # Patrón: historial clínico cronológico del paciente.
    db.consultations.create_index(
        [("patientId", ASCENDING), ("date", DESCENDING)],
        name="ix_paciente_fecha",
    )
    # Patrón: mapa de alertas activas en tiempo real.
    db.alerts.create_index(
        [("status", ASCENDING), ("createdAt", DESCENDING)],
        name="ix_estado_fecha",
    )
    db.alerts.create_index(
        [("patientId", ASCENDING), ("createdAt", DESCENDING)],
        name="ix_paciente_fecha",
    )
    # Patrón: red de referidos recorrida con $graphLookup.
    db.referrals.create_index(
        [("patientId", ASCENDING), ("fromDoctorId", ASCENDING)],
        name="ix_paciente_origen",
    )
    # Búsqueda de médicos por especialidad (stress test típico).
    db.doctors.create_index([("specialty", ASCENDING)], name="ix_especialidad")
    print("Índices creados.")


if __name__ == "__main__":
    create_collections()
    create_indexes()
    print(f"Base '{db.name}' lista.")
