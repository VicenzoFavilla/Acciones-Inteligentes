@echo off
echo Creating destination directory: C:\proyectos\acciones_inteligentes
if not exist "C:\proyectos\acciones_inteligentes" mkdir "C:\proyectos\acciones_inteligentes"

echo Moving files from "c:\Users\vitii\OneDrive\Escritorio\acciones_inteligentes" to "C:\proyectos\acciones_inteligentes"
rem Use robocopy to move. /E for recursive, /MOVE to delete source files/dirs after copy.
rem /NFL /NDL to reduce output noise if needed, but logging is good.
robocopy "c:\Users\vitii\OneDrive\Escritorio\acciones_inteligentes" "C:\proyectos\acciones_inteligentes" /E /MOVE /IS /IT /NP

if %ERRORLEVEL% GEQ 8 (
    echo Robocopy failed with error %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Move completed successfully.
