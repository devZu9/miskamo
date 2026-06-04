@echo off
cd /d "%~dp0"
echo ====================================
echo  Miskam'o — Windows Setup
echo ====================================
echo.

REM Check Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ first.
    pause
    exit /b 1
)

echo [1/5] Installing Python packages...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install -r requirements-test.txt

echo [2/5] Creating shared directories...
if not exist "_shared\_tmp" mkdir "_shared\_tmp"
if not exist "_shared\_output" mkdir "_shared\_output"
if not exist "libs" mkdir libs

echo [3/5] Downloading FluidSynth DLLs...
powershell -Command "& {
    $url = 'https://github.com/FluidSynth/fluidsynth/releases/download/v2.5.2/fluidsynth-v2.5.2-win10-x64-glib.zip'
    $zip = \"$env:TEMP\fluidsynth.zip\"
    try {
        Write-Host '  Downloading FluidSynth 2.5.2 (3.4 MB)...'
        Invoke-WebRequest -Uri $url -OutFile $zip -ErrorAction Stop
        Write-Host '  Extracting DLLs...'
        Expand-Archive -Path $zip -DestinationPath \"$env:TEMP\fluidsynth\" -Force
        xcopy /E /I /Y \"$env:TEMP\fluidsynth\fluidsynth-v2.5.2-win10-x64-glib\bin\*.dll\" \"libs\"
        Write-Host '  DLLs installed to libs/'
    } catch {
        Write-Host '  Download failed: ' $_.Exception.Message
        Write-Host '  You can manually download from:'
        Write-Host '  https://github.com/FluidSynth/fluidsynth/releases/tag/v2.5.2'
        Write-Host '  Extract *.dll from bin/ into libs/'
    }
}"

echo [4/5] Checking SoundFont...
if not exist "libs\FluidR3_GM.sf2" (
    echo [WARN] FluidR3_GM.sf2 not found.
    echo Download from: https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2
    echo Place in libs\FluidR3_GM.sf2
)

echo.
echo ====================================
echo  Setup complete!
echo  Run start_win_web_ui_gui.bat to launch
echo ====================================
pause
