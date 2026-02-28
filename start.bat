@echo off
chcp 65001 >nul

title FriScan - Serveur localhost:8000
color 0B

echo.
echo  ╔══════════════════════════════════════════╗
echo  ║     FriScan - Lancement du serveur      ║
echo  ╚══════════════════════════════════════════╝
echo.

:: Vérifier que l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo  [ERREUR] Environnement virtuel introuvable.
    echo  Lancez d'abord l'installation.
    echo.
    pause
    exit /b 1
)

:: Activer l'environnement virtuel
call venv\Scripts\activate.bat

:: Tuer tout processus déjà en écoute sur le port 8000
echo  [INFO] Vérification du port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING"') do (
    echo  [WARN] Processus %%a détecté sur le port 8000, arrêt en cours...
    taskkill /PID %%a /F >nul 2>&1
)
:: Petit délai pour laisser le port se libérer
timeout /t 1 /nobreak >nul

echo  [OK] Port 8000 libre.
echo.
echo  ══════════════════════════════════════════
echo   FriScan démarre sur http://localhost:8000
    echo   Appuyez sur Ctrl+C pour arrêter le serveur
    echo  ══════════════════════════════════════════
echo.

:: Ouvrir le navigateur automatiquement après un court délai
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:8000"

:: Lancer le serveur FastAPI
python -m uvicorn server.app:app --host 0.0.0.0 --port 8000

echo.
echo  [INFO] Serveur arrêté.
pause
