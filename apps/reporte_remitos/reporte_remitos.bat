@echo off
REM Activar entorno virtual
cd /d "x:\fasapython\sistema-fasa\reporte_remitos"
call ..\venv\Scripts\activate.bat

REM Ejecutar el script y guardar salida en log
python reporte.py
