@echo off
REM ============================================================
REM TapNQue Quick & Safe Local Data Reset Utility
REM Cleans test tickets, queues, and counters while strictly
REM preserving admin passwords, email, and API settings.
REM ============================================================
title TapNQue Data Reset
echo ============================================================
echo          TapNQue Safe Local Data ^& Queue Reset
echo ============================================================
echo.
python reset_queue_data.py %*
echo.
pause
