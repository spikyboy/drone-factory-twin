@echo off
REM ---------------------------------------------------------------------------
REM Launch the Swarmy Factory Twin in a local Omniverse Kit runtime (Windows).
REM Set KIT_PATH to your kit.exe (Kit SDK) or omni.create.exe (USD Composer).
REM ---------------------------------------------------------------------------
setlocal
if "%KIT_PATH%"=="" set KIT_PATH=%LOCALAPPDATA%\ov\pkg\kit\kit.exe
set APP=%~dp0apps\swarmy.twin.kit
echo Launching twin with %KIT_PATH%
"%KIT_PATH%" "%APP%" --ext-folder "%~dp0source\extensions"
endlocal
