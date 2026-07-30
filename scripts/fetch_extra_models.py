#!/usr/bin/env python3
"""
⚠ SUPERSEDED — use scripts/fetch_models.py instead.

This is an older version of that script: it's missing `maps_1024` and
`wikiart_1024` (both present in your current backend/models/), has a stray
`beetles_1024` entry that isn't one of your current models, and doesn't do
the integrity verification (size/HTML checks) that fetch_models.py added to
fix the "pickle data was truncated" issue.

Kept here only so nothing is silently deleted out from under you — safe to
remove this file once you've confirmed fetch_models.py covers everything
you need (as of this check, it does: all 11 current models are in it).

--- original docstring below ---

Fetch (and convert where needed) the five "weird/broken" checkpoints into
backend/models/<id>/<id>.pkl so the model_registry picks them up on restart.

Run from the repo root with the backend venv:

    backend/env/bin/python scripts/fetch_extra_models.py
    backend/env/bin/python scripts/fetch_extra_models.py --only brecahad_512 afhq_wild_512

Two checkpoint types:
  - "native"  : already in StyleGAN2-ADA-PyTorch format. Downloaded as-is.
  - "legacy"  : older TF StyleGAN2 .pkl. Run through the ADA-PyTorch legacy.py
                converter (found in backend/vendor/stylegan2/legacy.py).

Requirements:
    backend/env/bin/pip install requests gdown
    # and the ADA-PyTorch engine must already be cloned at:
    #   backend/vendor/stylegan2/   (contains legacy.py)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "backend" / "models"
LEGACY_PY = ROOT / "backend" / "vendor" / "stylegan2" / "legacy.py"
PY = sys.executable  # use the same interpreter that launched this script

# id -> how to fetch it
MODELS = {
    # --- drop-in: ADA-PyTorch native, no conversion ---
    "brecahad_512": {
        "type": "native",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/brecahad.pkl",
    },
    "afhq_wild_512": {
        "type": "native",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/afhqwild.pkl",
    },
    # --- legacy TF StyleGAN2: download then convert via legacy.py ---
    "lsun_horse_256": {
        "type": "legacy",
        # legacy.py can read the URL directly as --source
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-horse-config-f.pkl",
    },
    "trypophobia_1024": {
        "type": "legacy",
        "gdrive_id": "12yYXZymadSIj74Yue1Q7RrlbIqrXggo3",
    },
    "beetles_1024": {
        "type": "legacy",
        "gdrive_id": "1BOluDQSMzKLgJ3tipAD3tfq5p6AEv_-C",
    },
}


def download(url: str, dest: Path) -> None:
    import requests  # imported here so --help works without the dep installed
    print(f"  downloading {url}")
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)


def gdrive_download(file_id: str, dest: Path) -> None:
    import gdown
    print(f"  downloading gdrive:{file_id}")
    gdown.download(id=file_id, output=str(dest), quiet=False)


def convert_legacy(source: str, dest: Path) -> None:
    if not LEGACY_PY.exists():
        raise SystemExit(
            f"legacy.py not found at {LEGACY_PY}\n"
            "Clone the engine first:\n"
            "  git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git "
            "backend/vendor/stylegan2"
        )
    print(f"  converting -> {dest.name}")
    subprocess.run(
        [PY, str(LEGACY_PY), f"--source={source}", f"--dest={dest}"],
        check=True,
    )


def fetch_one(model_id: str, spec: dict) -> None:
    folder = MODELS_DIR / model_id
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{model_id}.pkl"

    if final.exists():
        print(f"[{model_id}] already present, skipping")
        return

    print(f"[{model_id}] ({spec['type']})")

    if spec["type"] == "native":
        download(spec["url"], final)

    elif spec["type"] == "legacy":
        if "url" in spec:
            # legacy.py reads remote URLs directly — no temp file needed
            convert_legacy(spec["url"], final)
        else:
            tmp = folder / f"{model_id}.legacy.pkl"
            gdrive_download(spec["gdrive_id"], tmp)
            convert_legacy(str(tmp), final)
            tmp.unlink(missing_ok=True)

    print(f"[{model_id}] done -> {final.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", help="subset of model ids to fetch")
    args = ap.parse_args()

    ids = args.only or list(MODELS)
    unknown = [i for i in ids if i not in MODELS]
    if unknown:
        raise SystemExit(f"unknown model id(s): {', '.join(unknown)}")

    for model_id in ids:
        try:
            fetch_one(model_id, MODELS[model_id])
        except Exception as e:  # keep going; one bad link shouldn't stop the rest
            print(f"[{model_id}] FAILED: {e}", file=sys.stderr)

    print("\nDone. Restart the backend to register new models, then:")
    print("  npm run stage:models   # before any distribution build")


if __name__ == "__main__":
    main()
