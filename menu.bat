@echo off
REM Doble clic para publicar el menu: valida el Excel y, si esta todo bien, actualiza el sitio.
cd /d "%~dp0"
python build.py
echo.
pause
