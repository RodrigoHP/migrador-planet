@echo off
cd /d "%~dp0frontend"

echo Instalando dependencias (se necessario)...
if not exist "node_modules" (
    npm install
)

echo.
echo Frontend rodando em http://localhost:5173
echo Pressione Ctrl+C para parar.
echo.

npm run dev
