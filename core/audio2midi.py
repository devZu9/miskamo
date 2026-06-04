"""
core/audio2midi.py — голос → инструмент (DDSP) → MIDI

CLI:
  python -c "from core.audio2midi import MiskamoEngine; ..."
"""

import argparse, sys
from pathlib import Path
import torch
import torchaudio
import numpy as np
import soundfile as sf
import pretty_midi
from omegaconf import OmegaConf
from scipy.ndimage import median_filter

ROOT = Path(__file__).parent / "DDSP-Timbre-Transfer"
sys.path.insert(0, str(ROOT))
from ddsp_model.model.autoencoder_wrapper import AutoEncoderWrapper


class MiskamoEngine:
    MODELS = {
        "sax": {
            "checkpoint": ROOT / "exported_model" / "sax_48k_last.pth",
            "config": ROOT / "configs" / "sax_48k.yaml",
            "name": "Saxophone",
        },
    }

    def __init__(self, instrument="sax", device=None):
        if instrument not in self.MODELS:
            raise KeyError(f"Instrument '{instrument}' not found. Available: {list(self.MODELS.keys())}")

        info = self.MODELS[instrument]
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.config = OmegaConf.load(str(info["config"]))
        self.target_sr = int(self.config.sample_rate)
        self.frame_ms = int(self.config.frame_resolution * 1000)
        self.frame_s = float(self.config.frame_resolution)
        self.hop_length = int(self.frame_s * self.target_sr)

        self.wrapper = AutoEncoderWrapper(self.config, device=self.device)
        ckpt = torch.load(str(info["checkpoint"]), map_location=self.device)
        if isinstance(ckpt, dict) and "model" in ckpt:
            ckpt = ckpt["model"]
        self.wrapper.model.load_state_dict(ckpt)
        self.wrapper.model.eval()

        print(f"[Miskam'o] Loaded '{info['name']}' on {self.device}")

    def load_audio(self, path):
        y, sr = sf.read(path)
        if y.ndim > 1:
            y = y.mean(axis=1)
        y = torch.from_numpy(y).float().unsqueeze(0)
        if sr != self.target_sr:
            y = torchaudio.functional.resample(y, sr, self.target_sr)
        return y.to(self.device)

    def process(self, input_path, output_audio=None, output_midi=None, add_reverb=True):
        y = self.load_audio(input_path)
        f0, conf = self.wrapper.get_f0(y)
        with torch.no_grad():
            outputs = self.wrapper.reconstruction(y, f0=f0, add_reverb=add_reverb)

        out = outputs.get("audio_reverb" if add_reverb else None, outputs["audio_synth"])
        if out.dim() == 3 and out.size(1) == 1:
            out = out.squeeze(1)

        if output_audio:
            sf.write(output_audio, out.squeeze().cpu().numpy(), self.target_sr)
            print(f"[Miskam'o] Audio saved: {output_audio}")

        if output_midi:
            self._f0_to_midi(
                f0.squeeze(0).cpu().numpy(),
                conf.squeeze(0).cpu().numpy(),
                output_midi
            )
            print(f"[Miskam'o] MIDI saved: {output_midi}")

        return {"audio": out, "f0": f0}

    def _f0_to_midi(self, f0_hz, conf, output_path):
        """Convert F0 + confidence → MIDI with proper onset/offset detection."""
        FRAME_S = self.frame_s
        MIN_NOTE_DUR = 0.08          # minimum note duration (seconds)
        GAP_FILL_S = 0.04            # max silence gap to bridge (seconds)
        HYST_CENTS = 30              # pitch change hysteresis (cents)
        MEDFILT_SIZE = 5             # median filter kernel (frames)
        CONF_THRESH = 0.35           # minimum confidence for note onset

        GAP_FILL = max(1, int(GAP_FILL_S / FRAME_S))
        N = len(f0_hz)

        # 1. Smooth F0 with median filter (remove frame-level jitter)
        f0_smooth = median_filter(f0_hz, size=MEDFILT_SIZE)

        # 2. Convert to MIDI note numbers
        note_float = np.where(f0_smooth > 0,
                              12 * np.log2(np.maximum(f0_smooth, 1) / 440.0) + 69, 0)
        midi_rounded = np.round(note_float).astype(int)

        # 3. Note segmentation with hysteresis + gap filling
        notes = []
        i = 0
        while i < N:
            if midi_rounded[i] <= 0 or conf[i] < CONF_THRESH:
                i += 1
                continue

            note_start = i
            current_note = midi_rounded[i]
            gap = 0
            last_valid = i

            while i < N:
                has_pitch = midi_rounded[i] > 0 and conf[i] >= CONF_THRESH

                if not has_pitch:
                    gap += 1
                    if gap > GAP_FILL:
                        break
                    i += 1
                    continue

                gap = 0

                if midi_rounded[i] == current_note:
                    last_valid = i
                    i += 1
                    continue

                # Different pitch — check hysteresis
                cents_diff = abs(note_float[i] - (current_note + 0.5)) * 100
                if cents_diff >= HYST_CENTS:
                    break

                last_valid = i
                i += 1

            note_end = last_valid + 1
            dur = (note_end - note_start) * FRAME_S
            if dur >= MIN_NOTE_DUR:
                mean_conf = float(np.mean(conf[note_start:note_end]))
                vel = max(40, min(120, int(mean_conf * 100 + 20)))
                notes.append(pretty_midi.Note(
                    velocity=vel,
                    pitch=int(current_note),
                    start=note_start * FRAME_S,
                    end=note_end * FRAME_S,
                ))

        # 4. Merge adjacent same-pitch notes with gap < GAP_FILL
        notes.sort(key=lambda n: (n.pitch, n.start))
        merged = []
        for n in notes:
            if merged and n.pitch == merged[-1].pitch:
                last = merged[-1]
                gap = n.start - last.end
                if gap <= GAP_FILL_S and gap >= 0:
                    last.end = n.end
                    last.velocity = max(last.velocity, n.velocity)
                    continue
            merged.append(n)

        # 5. Sort by start time
        merged.sort(key=lambda n: n.start)

        # 6. Write MIDI
        midi = pretty_midi.PrettyMIDI()
        inst = pretty_midi.Instrument(program=0)
        inst.notes = merged
        midi.instruments.append(inst)
        midi.write(str(output_path))


def main():
    p = argparse.ArgumentParser(description="Miskam'o: voice → instrument → MIDI")
    p.add_argument("input", help="Input WAV file (vocal/humming)")
    p.add_argument("--instrument", "-i", default="sax", choices=list(MiskamoEngine.MODELS.keys()),
                   help="Target instrument (default: sax)")
    p.add_argument("--output_audio", "-oa", help="Output audio WAV path")
    p.add_argument("--output_midi", "-om", default="output.mid", help="Output MIDI path")
    p.add_argument("--no_reverb", action="store_true", help="Disable reverb")
    args = p.parse_args()

    v2m = MiskamoEngine(instrument=args.instrument)
    v2m.process(
        args.input,
        output_audio=args.output_audio,
        output_midi=args.output_midi,
        add_reverb=not args.no_reverb,
    )


if __name__ == "__main__":
    main()
