@echo off
chcp 65001 >nul
title FrigoScan - Gestionnaire de frigo
color 0A

echo.
echo  ╔═══════════════════════════════════════╗
echo  ║        🧊 FrigoScan v1.0 🧊          ║
echo  ║   Gestionnaire de frigo intelligent   ║
echo  ╚═══════════════════════════════════════╝
echo.

REM --- Vérifier et tuer le processus sur le port 8000 ---
echo [1/4] Vérification du port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000 " ^| findstr "LISTENING" 2^>nul') do (
    echo       Port 8000 occupé par PID %%a - Arrêt en cours...
    taskkill /F /PID %%a >nul 2>&1
    timeout /t 2 /nobreak >nul
)
echo       Port 8000 libre.
echo.

REM --- Environnement Python ---
echo [2/4] Configuration de l'environnement Python...
cd /d "%~dp0"

REM Vérifier si Python est disponible
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ❌ ERREUR : Python n'est pas installé ou pas dans le PATH.
    echo     Téléchargez Python 3.10+ sur https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

REM Créer l'environnement virtuel si nécessaire
if not exist "venv" (
    echo       Création de l'environnement virtuel...
    python -m venv venv
    if errorlevel 1 (
        echo  ❌ Erreur lors de la création du venv
        pause
        exit /b 1
    )
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat
echo       Environnement virtuel activé.
echo.

REM --- Installation des dépendances ---
echo [3/4] Vérification des dépendances...
pip install -r requirements.txt --quiet --disable-pip-version-check 2>nul
if errorlevel 1 (
    echo       Installation complète des dépendances...
    pip install -r requirements.txt --disable-pip-version-check
    if errorlevel 1 (
        echo  ❌ Erreur lors de l'installation des dépendances
        pause
        exit /b 1
    )
)
echo       Dépendances OK.
echo.

REM --- Créer le dossier data si nécessaire ---
if not exist "server\data" mkdir "server\data"

REM --- Lancement du serveur ---
echo [4/4] Lancement du serveur FrigoScan...
echo.
echo  ╔═══════════════════════════════════════╗
echo  ║                                       ║
echo  ║   Application accessible sur :        ║
echo  ║   👉 http://localhost:8000            ║
echo  ║                                       ║
echo  ║   Appuyez sur Ctrl+C pour arrêter     ║
echo  ║                                       ║
echo  ╚═══════════════════════════════════════╝
echo.

REM Ouvrir le navigateur après un délai
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM Lancer uvicorn
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload

echo.
echo  FrigoScan arrêté.
pause
