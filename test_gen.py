"""Генерирует тестовый WAV с простой мелодией для проверки пайплайна"""
import numpy as np
import soundfile as sf

SR = 48000
DUR = 3.0
t = np.linspace(0, DUR, int(SR * DUR), endpoint=False)

# Простая мелодия: C4 E4 G4 C5
notes = [
    (261.63, 0.0, 0.6),
    (329.63, 0.6, 1.2),
    (392.00, 1.2, 1.8),
    (523.25, 1.8, 2.4),
    (0, 2.4, 3.0),
]

audio = np.zeros(int(SR * DUR))
for freq, start, end in notes:
    if freq > 0:
        mask = (t >= start) & (t < end)
        sig = 0.5 * np.sin(2 * np.pi * freq * t[mask])
        vibrato = 0.95 + 0.05 * np.sin(2 * np.pi * 5 * t[mask])
        audio[mask] = sig * vibrato

audio = audio / (np.abs(audio).max() + 1e-8)
sf.write("test_melody.wav", audio, SR)
print("Saved test_melody.wav")
