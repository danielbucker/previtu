@echo off
setlocal
cd /d %~dp0
set PYTHONWARNINGS=ignore

set PY_EXE=
if exist "venv_previtu_v6\Scripts\python.exe" set PY_EXE=venv_previtu_v6\Scripts\python.exe
if not defined PY_EXE set PY_EXE=python

echo Usando Python: %PY_EXE%
if not exist db.sqlite3 (
    echo Primeira execucao: preparando banco de dados...
    "%PY_EXE%" manage.py migrate --noinput
    echo.
    echo Crie seu usuario de login abaixo:
    "%PY_EXE%" manage.py createsuperuser
)

start "" http://127.0.0.1:8000/
"%PY_EXE%" manage.py runserver 127.0.0.1:8000 --insecure
pause
