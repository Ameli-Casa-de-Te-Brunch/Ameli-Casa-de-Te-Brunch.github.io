@echo off
REM Doble clic: valida, arma el sitio, y te muestra exactamente que se va a
REM subir. Te pide que escribas "si" antes de publicar de verdad.
cd /d "%~dp0"
python build.py --publicar
echo.
pause
