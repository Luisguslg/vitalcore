@echo off
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo IMPORTANTE: marca la casilla "Add Python to PATH" al instalar.
  pause
  exit /b 1
)

if not exist .env (
  echo ============================================================
  echo  FALTA el archivo .env con las credenciales de la base.
  echo  Pide el contenido a Luis y crea el archivo .env en esta
  echo  misma carpeta (usa .env.example como referencia).
  echo ============================================================
  pause
  exit /b 1
)

if not exist venv (
  echo Primera vez: creando entorno e instalando dependencias...
  echo (esto tarda 1-2 minutos, solo ocurre una vez)
  python -m venv venv
  venv\Scripts\python.exe -m pip install -q -r requirements.txt
)

echo ============================================================
echo  API de VitalCore corriendo.
echo  Documentacion interactiva:  http://127.0.0.1:8000/docs
echo  Cierra esta ventana o presiona Ctrl+C para detenerla.
echo ============================================================
venv\Scripts\python.exe -m uvicorn app.main:app
pause
