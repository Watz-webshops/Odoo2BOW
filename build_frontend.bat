@echo off
cd /d "C:\Users\ruben\.vscode\github repos\Odoo2BOW\Odoo2BOW\frontend"
echo Building frontend...
call npm run build
if %ERRORLEVEL% EQU 0 (
    echo Build successful!
    exit /b 0
) else (
    echo Build failed!
    exit /b 1
)
