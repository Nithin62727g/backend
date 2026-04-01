@echo off
echo ========================================
echo   MasterAI Backend Server (Flask)
echo ========================================
echo.
echo IMPORTANT: Make sure XAMPP MySQL/MariaDB is running first!
echo.
echo Starting Flask backend on port 8001...
echo Access at:    http://localhost:8001
echo Health check: http://localhost:8001/health
echo.
cd /d %~dp0
call venv\Scripts\activate
python main.py
pause
