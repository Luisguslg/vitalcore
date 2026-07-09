@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo ============================================================
echo  VitalCore - Carga de datos en MongoDB Atlas
echo  NO CIERRES esta ventana. Tarda varios minutos.
echo  (La VPN debe estar DESCONECTADA mientras corre esto)
echo ============================================================
echo.
venv\Scripts\python.exe -u scripts\seed.py 2>&1
if errorlevel 1 goto :error
echo.
echo Verificando datos cargados...
venv\Scripts\python.exe -u scripts\verify.py > logs\verificacion.log 2>&1
if errorlevel 1 goto :error
type logs\verificacion.log
echo.
echo ============================================================
echo  LISTO. Ya puedes reconectar la VPN y avisarle a Claude.
echo ============================================================
goto :fin
:error
echo.
echo ************************************************************
echo  HUBO UN ERROR. Reconecta la VPN y muestrale a Claude
echo  el mensaje de arriba (o el archivo logs\verificacion.log).
echo ************************************************************
:fin
echo.
pause
