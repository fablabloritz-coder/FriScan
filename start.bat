@echo off
echo ==============================
echo   FriScan - Demarrage
echo ==============================
echo.

cd /d "%~dp0"

:: Verifier que l'environnement virtuel existe
if not exist "venv\Scripts\activate.bat" (
    echo [!] Environnement virtuel non trouve.
    echo [*] Creation en cours...
    python -m venv venv
    if errorlevel 1 (
        echo [ERREUR] Python n'est pas installe ou non dans le PATH.
        echo Installez Python depuis https://www.python.org
        pause
        exit /b 1
    )
    echo [*] Installation des dependances...
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.
echo [*] Demarrage du serveur FriScan...
echo [*] Interface disponible sur : http://localhost:8000
echo [*] Documentation API sur    : http://localhost:8000/docs
echo.
echo Appuyez sur Ctrl+C pour arreter le serveur.
echo.

python -m uvicorn server.app:app --host 0.0.0.0 --port 8000

pause
