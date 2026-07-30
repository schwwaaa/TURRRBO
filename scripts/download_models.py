#!/usr/bin/env python3
"""
scripts/download_models.py
Downloads pretrained StyleGAN2 / StyleGAN2-ADA / MetFaces checkpoints
from NVIDIA's official URLs into the correct model subdirectories.

⚠  All downloaded weights are under NVIDIA's non-commercial research license.
   Do NOT redistribute the .pkl files or use them in commercial products.
   See: https://nvlabs.github.io/stylegan2/license.html

Usage:
    python scripts/download_models.py
    python scripts/download_models.py --models ffhq_1024 metfaces_1024
"""

import argparse
import hashlib
import urllib.request
from pathlib import Path

# ── Where models land ────────────────────────────────────────────────────────
# Every checkpoint goes to:   backend/models/<model_id>/<filename>.pkl
# This is the ONE canonical model directory for the whole project — the
# backend reads from it directly in dev, and `src-tauri/resources/models` is
# a symlink pointing at this same folder (set up once via `ln -s`, see
# TURRRBO_DEV_REFERENCE.md), so the Tauri bundler picks up the same files at
# build time. Never copy .pkl files anywhere else — there should only ever be
# ONE physical copy of these weights on disk.
BACKEND = Path(__file__).parent.parent / "backend"

MODELS = {
    "ffhq_1024": {
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/ffhq.pkl",
        "filename": "ffhq-res1024-mirror-stylegan2-noaug.pkl",
        "dir": BACKEND / "models" / "ffhq_1024",
        "size_mb": 329,
    },
    "metfaces_1024": {
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/metfaces.pkl",
        "filename": "metfaces-res1024-mirror-paper256-ada.pkl",
        "dir": BACKEND / "models" / "metfaces_1024",
        "size_mb": 329,
    },
    "lsun_churches_256": {
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-church-config-f.pkl",
        "filename": "stylegan2-church-config-f.pkl",
        "dir": BACKEND / "models" / "lsun_churches_256",
        "size_mb": 403,
    },
    "afhq_cats_512": {
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/afhqcat.pkl",
        "filename": "afhqcat.pkl",
        "dir": BACKEND / "models" / "afhq_cats_512",
        "size_mb": 329,
    },
    "lsun_cars_512": {
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-car-config-f.pkl",
        "filename": "stylegan2-car-config-f.pkl",
        "dir": BACKEND / "models" / "lsun_cars_512",
        "size_mb": 403,
    },
}

def download(url: str, dest: Path, size_mb: int):
    if dest.exists():
        print(f"  already present: {dest.name}")
        return

    print(f"  downloading {dest.name} (~{size_mb} MB)…")
    dest.parent.mkdir(parents=True, exist_ok=True)

    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            pct = min(100, downloaded * 100 // total_size)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r  [{bar}] {pct:3d}%", end="", flush=True)

    urllib.request.urlretrieve(url, dest, reporthook=progress)
    print(f"\r  ✓ {dest.name}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--models",
        nargs="*",
        default=list(MODELS.keys()),
        choices=list(MODELS.keys()),
        help="Which models to download (default: all)",
    )
    args = parser.parse_args()

    print("TURRRBO model downloader")
    print("========================")
    print("License: NVIDIA non-commercial research use only.")
    print("Do not redistribute these weights commercially.\n")

    for model_id in args.models:
        spec = MODELS[model_id]
        dest = spec["dir"] / spec["filename"]
        print(f"[{model_id}]")
        download(spec["url"], dest, spec["size_mb"])

    print("\nDone. Model cards are already present in backend/models/*/model_card.json")
    print("Add model_card.json for any custom models you train yourself.")


if __name__ == "__main__":
    main()
