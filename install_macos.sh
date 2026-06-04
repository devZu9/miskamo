#!/bin/bash
# Miskam'o — macOS Setup
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "===================================="
echo " Miskam'o — macOS Setup"
echo "===================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install Python 3.11+ first."
    exit 1
fi

echo "[1/4] Installing system dependencies (Homebrew)..."
if command -v brew &> /dev/null; then
    brew install fluidsynth libsndfile
else
    echo "[WARN] Homebrew not found. Install fluidsynth manually:"
    echo "  brew install fluidsynth libsndfile"
fi

echo "[2/4] Installing Python packages..."
pip3 install torch torchaudio
pip3 install -r requirements.txt
pip3 install -r requirements-test.txt

echo "[3/4] Creating shared directories..."
mkdir -p _shared/_tmp _shared/_output
mkdir -p libs

echo "[4/4] Checking SoundFont..."
if [ ! -f "libs/FluidR3_GM.sf2" ]; then
    echo "[WARN] FluidR3_GM.sf2 not found."
    echo "Download from: https://member.keymusician.com/Member/FluidR3_GM/FluidR3_GM.sf2"
    echo "Place in libs/FluidR3_GM.sf2"
fi

echo ""
echo "===================================="
echo "  Setup complete!"
echo "  Run start_mac_web_ui_cpu.sh to launch"
echo "===================================="
