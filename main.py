"""
Miskam'o — FastAPI server
Personal music assistant: voice → MIDI, generator, dataset, training
"""
import os
from pathlib import Path

os.environ.setdefault("PATH", "")
os.environ["PATH"] = str(Path(__file__).parent / "libs") + os.pathsep + str(Path(__file__).parent) + os.pathsep + os.environ["PATH"]

from core.app import create_app

app = create_app()

if __name__ == "__main__":
    import uvicorn, webbrowser, threading
    from core.config import load_settings
    s = load_settings()
    print(f"\n[Miskam'o] Server: http://127.0.0.1:7890")
    threading.Timer(1.5, lambda: webbrowser.open("http://127.0.0.1:7890")).start()
    uvicorn.run("main:app", host="127.0.0.1", port=7890, log_level="warning", reload=True)
