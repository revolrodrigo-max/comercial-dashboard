@echo off
echo === Setup Dashboard Comercial ===

set PYTHON=C:\Users\revol\AppData\Local\Programs\Python\Python312\python.exe

echo Instalando dependencias...
"%PYTHON%" -m pip install -r requirements.txt

echo.
echo === Instalacion completa ===
echo Para iniciar el dashboard ejecuta:  run.bat
