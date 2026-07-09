"""Medición de KPIs de la API: levanta el servidor, ejercita cada patrón de
acceso N veces con parámetros realistas, demuestra la generación de alerta
por umbral vía POST /readings y deja el reporte en logs/ (incluida la tabla
en Markdown lista para el documento técnico)."""
import json
import random
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000"
ITERATIONS = 30
random.seed(7)


def get(path):
    start = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=60) as resp:
        body = resp.read()
    ms = (time.perf_counter() - start) * 1000
    return ms, json.loads(body)


def post(path, payload):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
    ms = (time.perf_counter() - start) * 1000
    return ms, json.loads(body)


def wait_for_api(timeout=60):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            get("/health")
            return True
        except (urllib.error.URLError, ConnectionError, OSError):
            time.sleep(1.5)
    return False


def p95(samples):
    ordered = sorted(samples)
    return ordered[max(0, int(len(ordered) * 0.95) - 1)]


def main():
    (ROOT / "logs").mkdir(exist_ok=True)
    print("Levantando la API...")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8000"],
        cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        if not wait_for_api():
            print("ERROR: la API no respondió (¿VPN encendida?).")
            sys.exit(1)

        _, generals = get("/doctors?specialty=Medicina%20General")
        doctor_ids = [d["_id"] for d in generals]
        patient_ids = [f"P{i:04d}" for i in range(1, 501)]
        sensors = ["heart_rate", "glucose", "spo2", "blood_pressure_systolic"]
        months = [("2026-02-01", "2026-02-28"), ("2026-03-01", "2026-03-31"),
                  ("2026-04-01", "2026-04-30"), ("2026-05-01", "2026-05-31")]

        cases = {
            "P1 GET /patients/{id}/history":
                lambda: f"/patients/{random.choice(patient_ids)}/history",
            "P2 GET /patients/{id}/readings (sensor+rango)":
                lambda: "/patients/{}/readings?sensor={}&from={}&to={}".format(
                    random.choice(patient_ids), random.choice(sensors),
                    *random.choice(months)),
            "P3 GET /doctors/{id}/patients":
                lambda: f"/doctors/{random.choice(doctor_ids)}/patients",
            "P4 GET /alerts/active":
                lambda: "/alerts/active",
            "P5 GET /patients/{id}/referrals":
                lambda: f"/patients/{random.choice(patient_ids)}/referrals",
        }

        results = {}
        for label, make_path in cases.items():
            samples = [get(make_path())[0] for _ in range(ITERATIONS)]
            results[label] = samples
            print(f"  {label}: avg {statistics.mean(samples):.1f} ms "
                  f"(n={ITERATIONS})")

        # Demostración del patrón 4 en escritura: lectura crítica → alerta.
        print("\nDemostración de alerta por umbral (POST /readings)...")
        demo_pid = random.choice(patient_ids)
        ms_post, created = post("/readings", {
            "patientId": demo_pid, "sensorType": "glucose", "value": 320.0})
        _, active = get("/alerts/active?limit=5")
        alert_visible = any(a.get("_id") == created.get("alertId")
                            for a in active["alerts"])
        print(f"  paciente {demo_pid}, glucosa 320 mg/dL -> "
              f"isCritical={created['isCritical']}, "
              f"alerta visible en /alerts/active: {alert_visible} "
              f"({ms_post:.1f} ms)")

        _, metrics = get("/metrics")

        # Reporte legible + tabla Markdown para el documento técnico.
        lines = ["# Reporte de latencias — VitalCore API",
                 f"\nIteraciones por consulta: {ITERATIONS}. Cliente y servidor "
                 "en la misma máquina; la latencia incluye el viaje de red "
                 "hasta MongoDB Atlas (region US East).\n",
                 "| Patrón / Consulta | Promedio (ms) | p95 (ms) | Mín (ms) | Máx (ms) |",
                 "|---|---|---|---|---|"]
        for label, samples in results.items():
            lines.append(f"| {label} | {statistics.mean(samples):.1f} | "
                         f"{p95(samples):.1f} | {min(samples):.1f} | "
                         f"{max(samples):.1f} |")
        lines += [f"\n**Alerta por umbral (POST /readings):** lectura crítica "
                  f"insertada y alerta visible en /alerts/active en "
                  f"{ms_post:.1f} ms (paciente {demo_pid}, glucosa 320 mg/dL, "
                  f"alertId {created.get('alertId')}).",
                  "\n## Vista del servidor (colección metrics, GET /metrics)\n",
                  "| Endpoint | Método | Promedio (ms) | p95 (ms) | Requests |",
                  "|---|---|---|---|---|"]
        for row in metrics["queries"]:
            lines.append(f"| {row['endpoint']} | {row['method']} | "
                         f"{row['avgMs']} | {row.get('p95Ms', '—')} | "
                         f"{row['requests']} |")

        report = "\n".join(lines) + "\n"
        (ROOT / "logs" / "tabla_latencias.md").write_text(report, encoding="utf-8")
        print("\nReporte guardado en logs/tabla_latencias.md")
    finally:
        server.terminate()
    print("Medición completa.")


if __name__ == "__main__":
    main()
