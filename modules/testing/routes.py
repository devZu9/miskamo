"""testing module API endpoints."""
import sys, subprocess, threading, asyncio, json
from pathlib import Path
from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse, StreamingResponse

router = APIRouter()
ROOT = Path(__file__).resolve().parent.parent.parent


@router.post("/testing/run")
async def api_tests_run(filter: str = Form("")):
    async def event_stream():
        cmd = [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"]
        if filter:
            cmd.extend(["-k", filter])
        loop = asyncio.get_running_loop()
        queue = asyncio.Queue()

        def target():
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                cwd=str(ROOT), bufsize=0,
            )
            for line in iter(proc.stdout.readline, b''):
                decoded = line.decode('utf-8', errors='replace').rstrip()
                if decoded:
                    print(f"[Tests] {decoded}", flush=True)
                loop.call_soon_threadsafe(queue.put_nowait, ('line', line))
            proc.wait()
            loop.call_soon_threadsafe(queue.put_nowait, ('done', proc.returncode))

        threading.Thread(target=target, daemon=True).start()

        while True:
            typ, val = await queue.get()
            if typ == 'done':
                yield f"result:{json.dumps({'ok': val == 0, 'returncode': val})}\n"
                break
            decoded = val.decode('utf-8', errors='replace').rstrip()
            if decoded:
                yield f"log:{decoded}\n"

    return StreamingResponse(event_stream(), media_type="text/plain")
