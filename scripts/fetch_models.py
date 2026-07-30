#!/usr/bin/env python3
"""
scripts/fetch_models.py
Fetches every TURRRBO model checkpoint — all 11, from every source (NVIDIA
CDN, Google Drive, archive.org) — into the correct model subdirectories,
converting legacy TF-format checkpoints where needed.

This is the ONE model-fetching script for the project. It replaces both
download_models.py and fetch_extra_models.py (now deleted — everything
either of them did, this script also does, plus integrity verification on
every download, not just some of them).

⚠  All downloaded weights are under NVIDIA's non-commercial research license
   (or the license of their respective source, for the archive.org/Drive
   ones). Do NOT redistribute the .pkl files or use them in commercial
   products. See: https://nvlabs.github.io/stylegan2/license.html

Run from the repo root using the backend venv's python:

    backend/env/bin/python scripts/fetch_models.py
    backend/env/bin/python scripts/fetch_models.py --force
    backend/env/bin/python scripts/fetch_models.py --only afhq_wild_512 maps_1024

A file is only considered "done" if it passes an INTEGRITY check (correct
byte size where known, and never an HTML error page in disguise). Truncated,
partial, or corrupt files are deleted and re-fetched automatically —
existence alone is never trusted. This is the fix for the
"pickle data was truncated" error.

Requires:  backend/env/bin/python -m pip install requests gdown
For the legacy-converted models, the ADA-PyTorch engine must be cloned at:
           backend/vendor/stylegan2/   (provides legacy.py)
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# ── Where models land ────────────────────────────────────────────────────────
# Every checkpoint goes to:   backend/models/<model_id>/<filename>
# This is the ONE canonical model directory for the whole project — the
# backend reads from it directly in dev, and `src-tauri/resources/models` is
# a symlink pointing at this same folder, so the Tauri bundler picks up the
# same files at build/package time. Never copy .pkl files anywhere else —
# there should only ever be ONE physical copy of these weights on disk.
MODELS_DIR = ROOT / "backend" / "models"
LEGACY_PY = ROOT / "backend" / "vendor" / "stylegan2" / "legacy.py"
PY = sys.executable                 # use the interpreter that launched this script
MIN_BYTES = 5_000_000               # real checkpoints are >100 MB; reject HTML/partials

# ── All 11 current models ────────────────────────────────────────────────────
# kind:
#   "direct" — download as-is, no conversion. Used both for models already in
#              ADA-PyTorch format AND for older TF-format checkpoints
#              (lsun_churches_256, lsun_cars_512) that the backend's
#              StyleGANEngine already detects and loads at runtime
#              (see [StyleGANEngine] "detected TF format" in the backend log).
#   "legacy" — downloaded (or pulled from Drive) then run through
#              legacy.py to convert to ADA-PyTorch format before use.
#
# NOTE: lsun_horse_256 is fetched from the same TF-format host/path as
# lsun_churches_256 and lsun_cars_512, but is marked "legacy" (pre-converted)
# here rather than "direct" (runtime-detected) — that's carried over as-is
# from the original scripts. If that's meant to be "direct" like churches/
# cars, flag it and it's a one-line change; not altered here since it depends
# on backend loading behavior this script doesn't control.
MODELS = {
    # --- originally in download_models.py: NVIDIA CDN, no conversion ---
    "ffhq_1024": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/ffhq.pkl",
        "filename": "ffhq-res1024-mirror-stylegan2-noaug.pkl",
    },
    "metfaces_1024": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/metfaces.pkl",
        "filename": "metfaces-res1024-mirror-paper256-ada.pkl",
    },
    "lsun_churches_256": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-church-config-f.pkl",
        "filename": "stylegan2-church-config-f.pkl",
    },
    "afhq_cats_512": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/afhqcat.pkl",
        "filename": "afhqcat.pkl",
    },
    "lsun_cars_512": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-car-config-f.pkl",
        "filename": "stylegan2-car-config-f.pkl",
    },

    # --- originally in fetch_models.py: NVIDIA CDN, no conversion ---
    "brecahad_512": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/brecahad.pkl",
        "filename": "brecahad_512.pkl",
    },
    "afhq_wild_512": {
        "kind": "direct",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2-ada-pytorch/pretrained/afhqwild.pkl",
        "filename": "afhq_wild_512.pkl",
    },

    # --- originally in fetch_models.py: legacy TF checkpoints -> converted ---
    "lsun_horse_256": {
        "kind": "legacy",
        "url": "https://nvlabs-fi-cdn.nvidia.com/stylegan2/networks/stylegan2-horse-config-f.pkl",
        "filename": "lsun_horse_256.pkl",
    },
    # Google Drive: fragile (quota / virus-scan interstitial). May need manual download.
    "trypophobia_1024": {
        "kind": "legacy",
        "gdrive_id": "12yYXZymadSIj74Yue1Q7RrlbIqrXggo3",
        "filename": "trypophobia_1024.pkl",
    },
    # archive.org direct download (reliable host), official NVIDIA StyleGAN2 -> converts cleanly
    "maps_1024": {
        "kind": "legacy",
        "url": "https://archive.org/download/mapdreamer/mapdreamer.pkl",
        "filename": "maps_1024.pkl",
    },
    # archive.org direct download, pbaylies/stylegan2 fork -> conversion likely but not guaranteed
    "wikiart_1024": {
        "kind": "legacy",
        "url": "https://archive.org/download/wikiart-stylegan2-conditional-model/WikiArt_Uncond2.pkl",
        "filename": "wikiart_1024.pkl",
    },
}

# ── Custom / manually-placed models ─────────────────────────────────────────
# Some checkpoints have no fetchable URL at all — self-trained models, or
# anything you only have as a local file. There's nothing for this script to
# download for these; it just checks the file is actually there and looks
# valid (not empty/truncated) at the expected path, and tells you clearly if
# it isn't.
#
# To add one:
#   1. Add an entry below: "your_model_id": {"filename": "your_model_id.pkl"}
#   2. Physically place the file at:
#        backend/models/your_model_id/your_model_id.pkl
#   3. Write a matching backend/models/your_model_id/model_card.json
#      (see any existing model folder for the expected fields —
#      id, name, description, resolution, category, checkpoint_file, etc.)
#   4. Restart the backend — ModelRegistry scans backend/models/ on startup
#      and will pick it up automatically. No code changes needed elsewhere.
LOCAL_MODELS: dict[str, dict] = {
    # "my_custom_model": {"filename": "my_custom_model.pkl"},
}


# ── Integrity checking ───────────────────────────────────────────────────────

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


def mb(path: Path) -> int:
    return path.stat().st_size // 1_000_000


# ── Fetch mechanics ──────────────────────────────────────────────────────────

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


def verify_local(mid: str, spec: dict) -> bool:
    """Check a manually-placed model is actually there and looks valid.
    Never attempts to download — there's nowhere to download it from."""
    folder = MODELS_DIR / mid
    final = folder / spec.get("filename", f"{mid}.pkl")

    if is_valid(final):
        print(f"[{mid}] OK ({mb(final)} MB) — local, verified")
        return True

    print(f"[{mid}] MISSING or INVALID -> expected at {final.relative_to(ROOT)}")
    print(f"           this model has no URL — copy the .pkl there by hand, "
          f"then re-run this script to verify it.")
    return False


def fetch_one(mid: str, spec: dict, force: bool) -> None:
    folder = MODELS_DIR / mid
    folder.mkdir(parents=True, exist_ok=True)
    final = folder / spec["filename"]

    # Skip ONLY if the existing file is verified valid.
    if final.exists() and not force:
        expected = remote_size(spec["url"]) if "url" in spec else None
        if is_valid(final, expected):
            print(f"[{mid}] OK ({mb(final)} MB) — skipping")
            return
        print(f"[{mid}] existing file is truncated/invalid — re-fetching")
        final.unlink()

    print(f"[{mid}] ({spec['kind']})")

    if spec["kind"] == "direct":
        http_download(spec["url"], final)
        if not is_valid(final, remote_size(spec["url"])):
            raise RuntimeError("download failed verification (wrong size or HTML)")

    else:  # "legacy" -> convert via legacy.py
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
    ap.add_argument("--only", nargs="*", help="subset of model ids to fetch (default: all 11)")
    ap.add_argument("--force", action="store_true", help="re-fetch even if a valid file exists")
    args = ap.parse_args()

    ids = args.only or list(MODELS)
    unknown = [i for i in ids if i not in MODELS]
    if unknown:
        raise SystemExit(f"unknown model id(s): {', '.join(unknown)}")

    print("TURRRBO model fetcher")
    print("======================")
    print(f"Fetching {len(ids)} model(s). License: NVIDIA non-commercial research use only")
    print("(and the respective source license for archive.org/Drive-hosted ones).")
    print("Do not redistribute these weights commercially.\n")

    failures = []
    for mid in ids:
        try:
            fetch_one(mid, MODELS[mid], args.force)
        except Exception as e:
            print(f"[{mid}] FAILED: {e}", file=sys.stderr)
            failures.append(mid)

    # Local/manual models are checked, never fetched — no network attempt.
    if LOCAL_MODELS and not args.only:
        print("\nLocal / manually-placed models:")
        for mid, spec in LOCAL_MODELS.items():
            if not verify_local(mid, spec):
                failures.append(mid)

    print()
    if failures:
        print(f"Done with {len(failures)} failure(s): {', '.join(failures)}")
        print("(NVIDIA-CDN and archive.org models should always succeed. Drive models may "
              "need the manual step in RUNBOOK.md.)")
    else:
        print(f"All {len(ids)} model(s) fetched and verified.")
    print("Restart the backend to register new models. Run `npm run stage:models` before a build.")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
