@echo off
cd /d "%~dp0"
echo ====================================================
echo  Building AG Printers Production Windows Executable
echo ====================================================
call "%~dp0.venv\Scripts\pyinstaller.exe" "%~dp0AG_Printers.spec" --clean --noconfirm
if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Build completed successfully!
    echo Output directory: %~dp0dist\AG Printers\
    echo Executable: %~dp0dist\AG Printers\AG Printers.exe
    echo.
) else (
    echo.
    echo [ERROR] Build failed! Check the output above.
    echo.
)
pause
