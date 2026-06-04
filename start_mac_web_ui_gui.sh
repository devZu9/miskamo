#!/bin/bash
# Miskam'o — Start (macOS, GPU if available)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
echo "Starting Miskam'o (GPU)..."
echo "Open http://127.0.0.1:7890 in your browser"
python3 main.py
