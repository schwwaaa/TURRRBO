#!/usr/bin/env python3
"""
Fetch + verify + (where needed) convert the five extra TURRRBO checkpoints.

Run from the repo root using the backend venv's python:

    backend/.venv/bin/python scripts/fetch_models.py
    backend/.venv/bin/python scripts/fetch_models.py --force
    backend/.venv/bin/python scripts/fetch_models.py --only afhq_wild_512

A file is only considered "done" if it passes an INTEGRITY check (correct byte
size, not an HTML error page). Truncated, partial, or corrupt files are deleted
and re-downloaded automatically -- existence alone is never trusted. This is the
fix for the "pickle data was truncated" error.

Requires:  backend/.venv/bin/python -m pip install requests gdown
For the legacy models, the ADA-PyTorch engine must be cloned at:
           backend/vendor/stylegan2/   (provides legacy.py)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "backend" / "models"
LEGACY_PY = ROOT / "backend" / "vendor" / "stylegan2" / "legacy.py"
PY = sys.executable                 # use the interpreter that launched this script
MIN_BYTES = 5_000_000               # real checkpoints are >100 MB; reject HTML/partials

MODELS = {
    # --- NVIDIA CDN: reliable, no Google Drive, no gdown needed ---
    "brecahad_512": {
        "type": "native",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/brecahad.pkl",
    },
    "afhq_wild_512": {
        "type": "native",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/afhqwild.pkl",
    },
    "lsun_horse_256": {
        "type": "legacy",  # legacy.py reads the URL directly and converts
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-horse-config-f.pkl",
    },
    # --- Google Drive: fragile (quota / virus-scan interstitial). May need manual download. ---
    "trypophobia_1024": {"type": "legacy", "gdrive_id": "12yYXZymadSIj74Yue1Q7RrlbIqrXggo3"},
    # --- archive.org direct download (reliable host), official NVIDIA StyleGAN2 -> converts cleanly ---
    "maps_1024": {"type": "legacy", "url": "https://archive.org/download/mapdreamer/mapdreamer.pkl"},
    # --- archive.org direct download, pbaylies/stylegan2 fork -> conversion likely but not guaranteed ---
    "wikiart_1024": {"type": "legacy", "url": "https://archive.org/download/wikiart-stylegan2-conditional-model/WikiArt_Uncond2.pkl"},
}


def looks_like_html(path: Path) -> bool:
    try:
        with open(path, "rb") as f:
            head = f.read(512).lstrip().lower()
        return head.startswith(b"<!doctype") or head.startswith(b"<html")
    except OSError:
        return True


def remote_size(url: str):
    import requests
    try:
        r = requests.head(url, allow_redirects=True, timeout=30)
        return int(r.headers.get("content-length", 0)) or None
    except Exception:
        return None


def is_valid(path: Path, expected: int | None = None) -> bool:
    if not path.exists():
        return False
    size = path.stat().st_size
    if size < MIN_BYTES or looks_like_html(path):
        return False
    if expected is not None and size != expected:
        return False
    return True


def http_download(url: str, dest: Path) -> None:
    import requests
    print(f"  downloading {url}")
    with requests.get(url, stream=True, timeout=180) as r:
        r.raise_for_status()
        expected = int(r.headers.get("content-length", 0)) or None
        written = 0
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                written += len(chunk)
    if expected is not None and written != expected:
        raise RuntimeError(f"incomplete download: got {written} of {expected} bytes")


def gdrive_download(file_id: str, dest: Path) -> None:
    import gdown
    print(f"  downloading gdrive:{file_id}")
    gdown.download(id=file_id, output=str(dest), quiet=False)


def convert_legacy(source: str, dest: Path) -> None:
    if not LEGACY_PY.exists():
        raise RuntimeError(
            f"legacy.py not found at {LEGACY_PY}. Clone it first:\n"
            "  git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git "
            "backend/vendor/stylegan2"
        )
    print(f"  converting -> {dest.name}")
    subprocess.run([PY, str(LEGACY_PY), f"--source={source}", f"--dest={dest}"], check=True)


def mb(path: Path) -> int:
    return path.stat().st_size // 1_000_000


def fetch_one(mid: str, spec: dict, force: bool) -> None:
    folder = MODELS_DIR / mid
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / f"{mid}.pkl"

    # Skip ONLY if the existing file is verified valid.
    if final.exists() and not force:
        expected = remote_size(spec["url"]) if spec.get("type") == "native" else None
        if is_valid(final, expected):
            print(f"[{mid}] OK ({mb(final)} MB) — skipping")
            return
        print(f"[{mid}] existing file is truncated/invalid — re-fetching")
        final.unlink()

    print(f"[{mid}] ({spec['type']})")

    if spec["type"] == "native":
        http_download(spec["url"], final)
        if not is_valid(final, remote_size(spec["url"])):
            raise RuntimeError("download failed verification (wrong size or HTML)")

    else:  # legacy -> convert via legacy.py
        if "url" in spec:
            convert_legacy(spec["url"], final)
        else:
            tmp = folder / f"{mid}.legacy.pkl"
            gdrive_download(spec["gdrive_id"], tmp)
            if not is_valid(tmp):
                tmp.unlink(missing_ok=True)
                raise RuntimeError(
                    "Google Drive returned an HTML/interstitial page, not the .pkl "
                    "(quota or scan block). Download it manually in a browser, then run "
                    "legacy.py yourself — see RUNBOOK.md step 3."
                )
            convert_legacy(str(tmp), final)
            tmp.unlink(missing_ok=True)
        if not final.exists() or final.stat().st_size < MIN_BYTES:
            raise RuntimeError("conversion did not produce a valid .pkl")

    print(f"[{mid}] DONE -> {final.relative_to(ROOT)} ({mb(final)} MB)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--only", nargs="*", help="subset of model ids to fetch")
    ap.add_argument("--force", action="store_true", help="re-download even if a valid file exists")
    args = ap.parse_args()

    ids = args.only or list(MODELS)
    unknown = [i for i in ids if i not in MODELS]
    if unknown:
        raise SystemExit(f"unknown model id(s): {', '.join(unknown)}")

    failures = []
    for mid in ids:
        try:
            fetch_one(mid, MODELS[mid], args.force)
        except Exception as e:
            print(f"[{mid}] FAILED: {e}", file=sys.stderr)
            failures.append(mid)

    print()
    if failures:
        print(f"Done with {len(failures)} failure(s): {', '.join(failures)}")
        print("(The NVIDIA-CDN models should always succeed. Drive models may need the "
              "manual step in RUNBOOK.md.)")
    else:
        print("All models fetched and verified.")
    print("Restart the backend to register them. Run `npm run stage:models` before a build.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
