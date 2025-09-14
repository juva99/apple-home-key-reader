@echo off
REM HomeKit Reconnection Tool for Windows
REM This batch file provides easy access to common reconnection tasks

echo.
echo ===============================================
echo   Apple Home Key Reader - HomeKit Reconnection
echo ===============================================
echo.

:menu
echo Choose an option:
echo.
echo 1. Check Status
echo 2. Show QR Code  
echo 3. Restart Service
echo 4. Reset Pairing (WARNING: Removes all pairings)
echo 5. Check Configuration
echo 6. Exit
echo.
set /p choice="Enter your choice (1-6): "

if "%choice%"=="1" goto status
if "%choice%"=="2" goto qr
if "%choice%"=="3" goto restart
if "%choice%"=="4" goto reset
if "%choice%"=="5" goto config
if "%choice%"=="6" goto exit
echo Invalid choice. Please try again.
goto menu

:status
echo.
echo Checking status...
python reconnect_homekit.py --check-status
echo.
pause
goto menu

:qr
echo.
echo Displaying QR code...
python reconnect_homekit.py --show-qr
echo.
pause
goto menu

:restart
echo.
echo Restarting HomeKit service...
echo Press Ctrl+C to stop the service when ready.
python reconnect_homekit.py --restart-service
echo.
pause
goto menu

:reset
echo.
echo WARNING: This will remove ALL HomeKit pairings!
set /p confirm="Are you sure? (y/N): "
if /i "%confirm%"=="y" (
    python reconnect_homekit.py --reset-pairing
) else (
    echo Operation cancelled.
)
echo.
pause
goto menu

:config
echo.
echo Checking configuration...
python reconnect_homekit.py --repair-config
echo.
pause
goto menu

:exit
echo.
echo Goodbye!
exit /b 0
