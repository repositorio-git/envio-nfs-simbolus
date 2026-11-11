echo "%~dp0"

cd /d "%~dp0"

set "PATH=%~dp0.venv\Scripts;%PATH%"

start "RPA" "%~dp0.venv\Scripts\python.exe" "%~dp0tarefas.py"