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

echo [1/4] Installing Python packages...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
pip install -r requirements-test.txt

echo [2/4] Creating directories...
if not exist "_tmp" mkdir _tmp
if not exist "_output" mkdir _output
if not exist "dataset" mkdir dataset
if not exist "train_output" mkdir train_output

echo [3/4] Creating MIDI bank directories...
if not exist "_midi_banks\generated" mkdir _midi_banks\generated

echo [4/4] Checking SoundFont...
if not exist "FluidR3_GM.sf2" (
    echo [WARN] FluidR3_GM.sf2 not found.
    echo Download it and place in the project root.
)

echo.
echo ====================================
echo  Setup complete!
echo  Run start_web_ui_gui.bat to launch
echo ====================================
pause
