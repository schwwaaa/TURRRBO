#!/bin/bash
# scripts/build_dmg.sh
# Builds a fully self-contained TURRRBO.dmg — Python backend + all models bundled.
# Run from the project root: bash scripts/build_dmg.sh

set -e
cd "$(dirname "$0")/.."
ROOT=$(pwd)

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       TURRRBO — FULL DMG BUILD           ║"
echo "║       (models bundled — no extras)       ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Detect architecture ───────────────────────────────────────────────────────
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    TRIPLE="aarch64-apple-darwin"
else
    TRIPLE="x86_64-apple-darwin"
fi
echo "→ Architecture: $TRIPLE"

# ── Step 1: Download any missing model checkpoints ────────────────────────────
echo ""
echo "[ 1/5 ] Checking model checkpoints..."
backend/.venv/bin/python3 scripts/download_models.py
echo "→ All models present"

# ── Step 2: Stage models into src-tauri/resources/models/ ────────────────────
echo ""
echo "[ 2/5 ] Staging models into bundle resources..."

STAGED="$ROOT/backend/models/models"
rm -rf "$STAGED"
mkdir -p "$STAGED"

for model_dir in "$ROOT/backend/models"/*/; do
    model_name=$(basename "$model_dir")
    mkdir -p "$STAGED/$model_name"
    # Copy model card
    cp "$model_dir/model_card.json" "$STAGED/$model_name/"
    # Copy any .pkl checkpoint
    for pkl in "$model_dir"*.pkl; do
        [ -f "$pkl" ] && cp "$pkl" "$STAGED/$model_name/" && echo "  → staged: $model_name/$(basename $pkl)"
    done
done

# Stage presets too
STAGED_PRESETS="$ROOT/src-tauri/resources/presets"
rm -rf "$STAGED_PRESETS"
cp -r "$ROOT/backend/presets" "$STAGED_PRESETS"
echo "→ Models staged"

# ── Step 3: Build Python sidecar ─────────────────────────────────────────────
echo ""
echo "[ 3/5 ] Building Python sidecar (this takes a few minutes)..."

mkdir -p "$ROOT/src-tauri/binaries"

backend/.venv/bin/python3 -m PyInstaller \
    --clean \
    --noconfirm \
    --distpath "$ROOT/src-tauri/binaries/_dist" \
    --workpath "$ROOT/build/pyinstaller" \
    backend/turrrbo_backend.spec

SIDECAR="$ROOT/src-tauri/binaries/turrrbo-backend-$TRIPLE"
cp "$ROOT/src-tauri/binaries/_dist/turrrbo-backend" "$SIDECAR"
chmod +x "$SIDECAR"
echo "→ Sidecar: $(basename $SIDECAR)"

# ── Step 4: Create icons ──────────────────────────────────────────────────────
echo ""
echo "[ 4/5 ] Creating icons..."

mkdir -p "$ROOT/src-tauri/icons"

backend/.venv/bin/python3 - << 'PYEOF'
from PIL import Image, ImageDraw
import os
from pathlib import Path

icons_dir = Path("src-tauri/icons")
icons_dir.mkdir(parents=True, exist_ok=True)

def make_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size, size], radius=size//5, fill=(13, 13, 13, 255))
    pad = size // 5
    thick = max(2, size // 16)
    accent = (200, 255, 0, 255)
    d.rectangle([pad, pad, size - pad, pad + thick * 2], fill=accent)
    mid = size // 2 - thick
    d.rectangle([mid, pad, mid + thick * 2, size - pad], fill=accent)
    return img

for s in [16, 32, 64, 128, 256, 512, 1024]:
    make_icon(s).save(str(icons_dir / f"{s}x{s}.png"))

make_icon(32).save(str(icons_dir / "32x32.png"))
make_icon(128).save(str(icons_dir / "128x128.png"))
make_icon(256).save(str(icons_dir / "128x128@2x.png"))
make_icon(512).save(str(icons_dir / "icon.png"))
print("→ PNG icons created")
PYEOF

ICONSET="$ROOT/src-tauri/icons/icon.iconset"
mkdir -p "$ICONSET"
cp "$ROOT/src-tauri/icons/16x16.png"    "$ICONSET/icon_16x16.png"
cp "$ROOT/src-tauri/icons/32x32.png"    "$ICONSET/icon_16x16@2x.png"
cp "$ROOT/src-tauri/icons/32x32.png"    "$ICONSET/icon_32x32.png"
cp "$ROOT/src-tauri/icons/64x64.png"    "$ICONSET/icon_32x32@2x.png"
cp "$ROOT/src-tauri/icons/128x128.png"  "$ICONSET/icon_128x128.png"
cp "$ROOT/src-tauri/icons/256x256.png"  "$ICONSET/icon_128x128@2x.png"
cp "$ROOT/src-tauri/icons/256x256.png"  "$ICONSET/icon_256x256.png"
cp "$ROOT/src-tauri/icons/512x512.png"  "$ICONSET/icon_256x256@2x.png"
cp "$ROOT/src-tauri/icons/512x512.png"  "$ICONSET/icon_512x512.png"
cp "$ROOT/src-tauri/icons/1024x1024.png" "$ICONSET/icon_512x512@2x.png"
iconutil -c icns "$ICONSET" -o "$ROOT/src-tauri/icons/icon.icns"
echo "→ .icns created"

# ── Step 5: Update tauri.conf.json and build ──────────────────────────────────
echo ""
echo "[ 5/5 ] Configuring tauri.conf.json and building..."

backend/.venv/bin/python3 - << 'PYEOF'
import json
from pathlib import Path

path = Path("src-tauri/tauri.conf.json")
cfg = json.load(open(path))

cfg["tauri"]["bundle"]["icon"] = [
    "icons/32x32.png",
    "icons/128x128.png",
    "icons/128x128@2x.png",
    "icons/icon.icns",
    "icons/icon.png",
]
cfg["tauri"]["bundle"]["externalBin"] = ["binaries/turrrbo-backend"]
cfg["tauri"]["bundle"]["resources"] = [
    "resources/models/**",
    "resources/presets/**",
    "resources/licenses/**",
]
cfg["tauri"]["allowlist"]["shell"]["sidecar"] = True

json.dump(cfg, open(path, "w"), indent=2)
print("→ tauri.conf.json updated")
PYEOF

npm run build
npx tauri build

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   BUILD COMPLETE ✓                       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "→ .dmg: src-tauri/target/release/bundle/dmg/"
echo "→ .app: src-tauri/target/release/bundle/macos/"
echo ""
echo "The .dmg contains:"
echo "  • TURRRBO app"
echo "  • Python backend (no Python install needed)"
echo "  • All model checkpoints"
echo "  • Default presets"
echo "  Users need nothing else."
