@echo off
REM Doble clic: valida el Excel y arma el sitio en tu PC (dist/index.html).
REM Esto NO publica nada. Para publicar de verdad, usa publicar.bat.
cd /d "%~dp0"
python build.py
echo.
pause
