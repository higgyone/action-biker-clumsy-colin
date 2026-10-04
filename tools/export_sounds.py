"""Write every sound of the port as a WAV file so it can be played outside the game.

Usage: python tools/export_sounds.py        (run from the repo root; writes work/sounds/*.wav)
"""
import json
import os
import sys
import wave

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "port"))
os.chdir(ROOT)
import sound   # noqa: E402

os.makedirs("work/sounds", exist_ok=True)
for name, samples in sound.samples(json.load(open("assets/sounds.json"))).items():
    path = f"work/sounds/{name}.wav"
    with wave.open(path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sound.RATE)
        f.writeframes(samples.tobytes())
    print(f"{path}: {len(samples) / sound.RATE:.3f} s")
