#!/bin/bash
# Miskam'o — Start (CPU only)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
echo "Starting Miskam'o (CPU)..."
echo "Open http://127.0.0.1:7890 in your browser"
export CUDA_VISIBLE_DEVICES=-1
python3 main.py
