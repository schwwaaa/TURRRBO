#!/usr/bin/env python3
"""
scripts/build_sidecar.py
Bundles the Python backend into a single-file executable that Tauri can
ship as a sidecar binary.

Usage (from project root):
    python scripts/build_sidecar.py

Output:
    src-tauri/binaries/python-sidecar-<target-triple>
    (Tauri's expected sidecar naming convention)

Requirements:
    pip install pyinstaller
    All backend/requirements.txt dependencies installed
"""

import os
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
BACKEND = ROOT / "backend"
ENTRY   = BACKEND / "api" / "server.py"
OUT_DIR = ROOT / "src-tauri" / "binaries"

# Determine Tauri target triple suffix
def get_target_triple() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "darwin":
        arch = "aarch64" if machine == "arm64" else "x86_64"
        return f"{arch}-apple-darwin"
    elif system == "windows":
        return "x86_64-pc-windows-msvc"
    else:
        return "x86_64-unknown-linux-gnu"

def build():
    triple = get_target_triple()
    binary_name = f"python-sidecar-{triple}"
    print(f"[build_sidecar] target triple: {triple}")
    print(f"[build_sidecar] output: {OUT_DIR / binary_name}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Collect hidden imports from stylegan2-ada-pytorch
    hidden = [
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "torch",
        "numpy",
        "PIL",
    ]

    hidden_flags = []
    for h in hidden:
        hidden_flags += ["--hidden-import", h]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--name", binary_name,
        "--distpath", str(OUT_DIR),
        "--workpath", str(ROOT / "build" / "pyinstaller"),
        "--specpath", str(ROOT / "build"),
        # Include the stylegan2 vendor directory
        "--add-data", f"{BACKEND / 'vendor' / 'stylegan2'}{os.pathsep}stylegan2",
        # Include presets and model cards (not .pkl files — too large; those ship separately)
        "--add-data", f"{BACKEND / 'presets'}{os.pathsep}presets",
        *hidden_flags,
        str(ENTRY),
    ]

    print(f"[build_sidecar] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print("[build_sidecar] ✕ PyInstaller failed")
        sys.exit(1)

    print(f"[build_sidecar] ✓ built {OUT_DIR / binary_name}")

if __name__ == "__main__":
    build()
