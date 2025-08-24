@echo off
rem File ini sekarang adalah launcher pintar yang akan memeriksa update terlebih dahulu.

echo =======================================================
echo          FLOWORK SMART LAUNCHER
echo =======================================================
echo.

echo [TAHAP 1/3] Memeriksa pembaruan dari GitHub...
echo -------------------------------------------------------
poetry run python updater.py
echo -------------------------------------------------------
echo.

echo [TAHAP 2/3] Memeriksa lisensi dan versi...
echo [TAHAP 3/3] Menjalankan Flowork...
echo -------------------------------------------------------
rem Menjalankan launcher utama yang akan memulai aplikasi Flowork
poetry run python launcher.py
echo -------------------------------------------------------
echo.

echo Proses selesai. Tekan tombol apa saja untuk keluar.
pause >nul