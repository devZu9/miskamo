"""E2E tests: mock heavy deps so uvicorn can start without torch/fluidsynth."""

import io
import os
import sys
from unittest.mock import MagicMock
import numpy as np

os.environ.setdefault("MPLBACKEND", "Agg")
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

# Mock core.audio2midi (imports torch, loads GPU model)
def _fake_process(in_path, out_wav, out_mid, reverb=True):
    from pathlib import Path
    Path(out_wav).write_bytes(b"RIFF" + b"\x00" * 4092)
    Path(out_mid).write_bytes(b"MThd" + b"\x00" * 10)
    return {
        "audio": Path(out_wav).name,
        "midi": Path(out_mid).name,
        "f0": [260.0, 262.0],
        "notes": [(60, 0.0, 1.0, 80), (62, 1.0, 2.0, 80)],
    }

_mock_engine = MagicMock()
_mock_engine.process.side_effect = _fake_process
_mock_audio2midi = MagicMock()
_mock_audio2midi.MiskamoEngine = MagicMock(return_value=_mock_engine)
sys.modules["core.audio2midi"] = _mock_audio2midi

# Mock core.fluidsynth (requires native SF2 + DLLs)
_mock_fluidsynth = MagicMock()
_mock_fluidsynth._render_midi = MagicMock(return_value=io.BytesIO(b"RIFF\x00" * 256))
_mock_fluidsynth._notes_to_audio = MagicMock(return_value=np.zeros(44100, np.float32))
_mock_fluidsynth._get_synth = MagicMock(return_value=MagicMock())
sys.modules["core.fluidsynth"] = _mock_fluidsynth
