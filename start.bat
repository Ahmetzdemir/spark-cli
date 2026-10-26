@echo off
chcp 65001 > nul
echo ========================================================
echo       Spark CLI - Yerel AI Kodlama Asistani
echo ========================================================
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [HATA] .venv sanal ortami bulunamadi!
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [1/2] Baglanti kontrol ediliyor (LM Studio / Local LLM)...
python -m spark.cli test
echo.

echo [2/2] Spark CLI baslatiliyor...
echo.
python -m spark.cli %*

pause
