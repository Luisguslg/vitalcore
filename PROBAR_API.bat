@echo off
cd /d "%~dp0"
echo ============================================================
echo  VitalCore - Medicion de KPIs de la API
echo  (La VPN debe estar DESCONECTADA mientras corre esto)
echo  Ejercita los 5 patrones de acceso, demuestra la alerta
echo  por umbral y guarda el reporte en logs\tabla_latencias.md
echo ============================================================
echo.
venv\Scripts\python.exe -u scripts\measure_api.py
if errorlevel 1 (
  echo.
  echo ************************************************************
  echo  HUBO UN ERROR. Reconecta la VPN y muestrale a Claude el
  echo  mensaje de arriba.
  echo ************************************************************
) else (
  echo.
  echo ============================================================
  echo  LISTO. Ya puedes reconectar la VPN y avisarle a Claude.
  echo ============================================================
)
echo.
pause
