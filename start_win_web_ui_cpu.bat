@echo off
cd /d "%~dp0"
echo Starting Miskam'o (CPU)...
echo Open http://127.0.0.1:7890 in your browser
set CUDA_VISIBLE_DEVICES=-1
python main.py
pause
