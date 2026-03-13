@echo off
cd /d "%~dp0backend"

if not exist ".venv" (
    echo Criando ambiente virtual...
    python -m venv .venv
)

call .venv\Scripts\activate

echo Instalando/atualizando dependencias...
pip install -r requirements.txt -q

echo.
echo Backend rodando em http://localhost:8000
echo Swagger UI: http://localhost:8000/docs
echo Pressione Ctrl+C para parar.
echo.

uvicorn main:app --reload --port 8000
