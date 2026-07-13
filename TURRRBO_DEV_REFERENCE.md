# TURRRBO — Internal Developer Reference

> Keep this document. Every time something breaks, the answer is in here.

---

## THE GOLDEN RULE

There are two different environments. They behave differently. Confusing them causes most problems.

| | Dev Mode | Bundled App |
|---|---|---|
| Launch command | `npm run tauri:dev` | Open TURRRBO.app |
| Python backend | Started by `concurrently` in your terminal | PyInstaller binary baked into the .app |
| Frontend | Vite hot-reload (instant changes) | Compiled into the bundle |
| Rust | Recompiles on file save (~30–90s) | Pre-compiled |
| **When you change Python** | Restart `npm run tauri:dev` | **Must rebuild sidecar + app** |
| **When you change React/TS** | Auto hot-reloads | Must rebuild app |
| **When you change Rust** | Auto recompiles | Must rebuild app |

---

## RUNNING THE PROJECT

### Dev mode (daily development)

```bash
cd "/Users/tgm/Downloads/turrrbo"
npm run tauri:dev
```

This starts:
1. The Python backend on port 47474
2. Vite dev server on port 5173
3. The Tauri window pointing at Vite

**Stop it:** `Ctrl+C`

---

### Building the app

#### Step 1 — Build the Python sidecar (only needed when Python files change)

```bash
cd "/Users/tgm/Downloads/turrrbo"

backend/.venv/bin/python3 -m PyInstaller \
    --clean --noconfirm \
    --distpath "src-tauri/binaries/_dist" \
    --workpath "build/pyinstaller" \
    backend/turrrbo_backend.spec

cp src-tauri/binaries/_dist/turrrbo-backend \
   src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin

chmod +x src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin
```

#### Step 2 — Build the Tauri app

```bash
npm run tauri:build
```

Output: `src-tauri/target/release/bundle/macos/TURRRBO.app`

#### Step 3 — Create the DMG

```bash
npm run make:dmg
```

Output: `src-tauri/target/release/bundle/dmg/TURRRBO_0.1.0.dmg`

---

### Full rebuild from scratch (everything)

```bash
cd "/Users/tgm/Downloads/turrrbo"

backend/.venv/bin/python3 -m PyInstaller \
    --clean --noconfirm \
    --distpath "src-tauri/binaries/_dist" \
    --workpath "build/pyinstaller" \
    backend/turrrbo_backend.spec

cp src-tauri/binaries/_dist/turrrbo-backend \
   src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin

chmod +x src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin

npm run tauri:build
npm run make:dmg
```

---

## WHEN THINGS BREAK — FIX GUIDE

### "Missing script: tauri:dev" or "Missing script: tauri:build"

The scripts got lost from `package.json`. Run:

```bash
cd "/Users/tgm/Downloads/turrrbo"

node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.scripts['backend'] = 'backend/.venv/bin/python3 backend/api/server.py --port 47474';
pkg.scripts['tauri:dev'] = 'concurrently -k -n BACKEND,TAURI -c cyan,yellow \"npm run backend\" \"npm run tauri dev\"';
pkg.scripts['tauri:build'] = 'npm run build && npx tauri build --bundles app';
pkg.scripts['make:dmg'] = 'APP=\"src-tauri/target/release/bundle/macos/TURRRBO.app\" && DMG=\"src-tauri/target/release/bundle/dmg/TURRRBO_0.1.0.dmg\" && mkdir -p src-tauri/target/release/bundle/dmg && STAGING=\$(mktemp -d) && cp -r \"\$APP\" \"\$STAGING/TURRRBO.app\" && ln -s /Applications \"\$STAGING/Applications\" && hdiutil create -volname TURRRBO -srcfolder \"\$STAGING\" -ov -format UDZO \"\$DMG\" && rm -rf \"\$STAGING\" && echo \"Built: \$DMG\"';
pkg.devDependencies['concurrently'] = '^8.2.0';
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
console.log('done');
"

npm install
```

---

### Backend not starting / "Starting backend..." forever

**In dev mode:**
Check the terminal for Python errors. The most common causes:

```bash
# Is the port already in use?
kill $(lsof -ti:47474) 2>/dev/null || true

# Then restart
npm run tauri:dev
```

**In the bundled app:**
Run the app from Terminal to see backend logs:

```bash
/Applications/TURRRBO.app/Contents/MacOS/TURRRBO
# or for the dev bundle:
/Users/tgm/Downloads/turrrbo/src-tauri/target/release/bundle/macos/TURRRBO.app/Contents/MacOS/TURRRBO
```

The logs will show exactly why the backend failed.

---

### "No module named X" — any module (numpy, torch, clip, etc.)

This only happens in the **bundled app**. Dev mode uses the real venv and always has all modules.

The module wasn't included by PyInstaller. Fix:

1. Install it in the venv:
```bash
backend/.venv/bin/pip install <module-name>
```

2. Add it to `backend/turrrbo_backend.spec` in the `hiddenimports` list if it's a pure Python module, or use `collect_all("module_name")` if it has compiled extensions.

3. Rebuild the sidecar and app (see Full Rebuild above).

**Special case — numpy:**
Always pin numpy below 2.0. StyleGAN2 uses the old `numpy.core` API:
```bash
backend/.venv/bin/pip install "numpy<2.0"
```

---

### "could not get source code" — Automotive Drift / Haunted Schematics

These are old TF-format checkpoints. The fix is in `inference.py` — a patch to `inspect.getsource`. Verify it's there:

```bash
grep -n "safe_getsource" backend/stylegan_engine/inference.py
```

If that returns nothing, the fix is missing. Add it manually to `load_model()` in `inference.py` just before the `import dnnlib` line:

```python
import inspect as _inspect
_orig_getsource = _inspect.getsource
def _safe_getsource(obj, **kwargs):
    try:
        return _orig_getsource(obj, **kwargs)
    except (OSError, TypeError):
        return ""
_inspect.getsource = _safe_getsource

import dnnlib
import legacy

with dnnlib.util.open_url(checkpoint) as f:
    data = legacy.load_network_pkl(f)

_inspect.getsource = _orig_getsource  # restore
```

Then rebuild the sidecar and app.

---

### Tauri build fails — "path matching X not found"

A file listed in `tauri.conf.json` under `resources` doesn't exist. Tauri refuses to build if any listed resource is missing.

Check what's listed:
```bash
python3 -c "
import json
cfg = json.load(open('src-tauri/tauri.conf.json'))
print(json.dumps(cfg['tauri']['bundle']['resources'], indent=2))
"
```

Every file listed must exist at that path relative to `src-tauri/`. Either create the missing file or remove it from the list.

The safest approach is to list files explicitly (not globs). Globs crash if the directory is empty.

---

### Tauri build fails — icon errors

Icons must exist at the paths listed in `tauri.conf.json`:

```bash
ls src-tauri/icons/
```

If missing, regenerate them:

```bash
mkdir -p src-tauri/icons
backend/.venv/bin/python3 -c "
from PIL import Image, ImageDraw
from pathlib import Path

icons_dir = Path('src-tauri/icons')
icons_dir.mkdir(parents=True, exist_ok=True)

def make_icon(size):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
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
    make_icon(s).save(str(icons_dir / f'{s}x{s}.png'))

make_icon(32).save(str(icons_dir / '32x32.png'))
make_icon(128).save(str(icons_dir / '128x128.png'))
make_icon(256).save(str(icons_dir / '128x128@2x.png'))
make_icon(512).save(str(icons_dir / 'icon.png'))
print('done')
"

ICONSET="src-tauri/icons/icon.iconset"
mkdir -p "$ICONSET"
cp src-tauri/icons/16x16.png    "$ICONSET/icon_16x16.png"
cp src-tauri/icons/32x32.png    "$ICONSET/icon_16x16@2x.png"
cp src-tauri/icons/32x32.png    "$ICONSET/icon_32x32.png"
cp src-tauri/icons/64x64.png    "$ICONSET/icon_32x32@2x.png"
cp src-tauri/icons/128x128.png  "$ICONSET/icon_128x128.png"
cp src-tauri/icons/256x256.png  "$ICONSET/icon_128x128@2x.png"
cp src-tauri/icons/256x256.png  "$ICONSET/icon_256x256.png"
cp src-tauri/icons/512x512.png  "$ICONSET/icon_256x256@2x.png"
cp src-tauri/icons/512x512.png  "$ICONSET/icon_512x512.png"
cp src-tauri/icons/1024x1024.png "$ICONSET/icon_512x512@2x.png"
iconutil -c icns "$ICONSET" -o src-tauri/icons/icon.icns
```

---

### Rust compile errors

**"no method named shell found"** — wrong Tauri API. Use `tauri::api::process::Command` or `std::process::Command` instead of `app.shell()`.

**"could not compile — E0597 does not live long enough"** — lifetime issue with MutexGuard. Pattern:
```rust
// Wrong
let port = *app.state::<AppState>().sidecar_port.lock().unwrap();

// Right
let port = {
    let s = app.state::<AppState>();
    let x = *s.sidecar_port.lock().unwrap(); x
};
```

**"unresolved import"** — check Cargo.toml features. The feature must be listed for the API to be available.

---

### Generation fails in dev but works in app (or vice versa)

**Fails in dev, works in app:** Unlikely. Dev uses the real venv. Check if the venv is activated correctly and the backend started.

**Fails in app, works in dev:** Python module missing from PyInstaller bundle. See "No module named X" above.

**Fails in both:** The error is in inference logic. Run the app from Terminal to see the full Python traceback.

---

### Spacebar triggers generation when typing

Keyboard shortcuts must exclude `HTMLTextAreaElement`:

```typescript
if (
  e.target instanceof HTMLInputElement ||
  e.target instanceof HTMLSelectElement ||
  e.target instanceof HTMLTextAreaElement  // ← this line
) return;
```

If missing from `App.tsx`, add it.

---

### Images not displaying in the UI

The Tauri asset protocol must be enabled in `tauri.conf.json`:

```json
"protocol": {
  "asset": true,
  "assetScope": ["$HOME/**", "/Users/**", "/tmp/**"]
}
```

Without this, `convertFileSrc()` in the React frontend produces URLs that Tauri blocks.

---

### Port 47474 already in use

A previous backend process is still running. Kill it:

```bash
kill $(lsof -ti:47474) 2>/dev/null || true
```

Then restart dev mode.

---

## ADDING A NEW MODEL

1. Create a folder: `backend/models/your_model_id/`
2. Copy the `.pkl` checkpoint into it
3. Create `model_card.json`:

```json
{
  "id": "your_model_id",
  "name": "Display Name",
  "description": "What it produces.",
  "resolution": 512,
  "category": "face",
  "provenance": "Source and license.",
  "checkpoint_file": "your_checkpoint.pkl",
  "recommended_psi": 0.7,
  "tags": ["tag1", "tag2"]
}
```

4. **Dev mode:** restart `npm run tauri:dev` — model appears automatically
5. **Bundled app:** rebuild sidecar + app (models are staged into the bundle during build)

---

## ADDING A NEW STYLE ROUTE

Edit `backend/stylegan_engine/style_routes.py`. Add an entry to `STYLE_ROUTES`:

```python
{
    "id": "your_route_id",
    "label": "Your Route Name",
    "description": "What it does artistically.",
    "psi_offset": 0.2,            # added to user's truncation_psi
    "noise_mode_override": None,   # or "const" / "random" / "none"
    "mix_layer_preset": None,      # or [0,1,2,3] etc
},
```

No other files need changing. The route appears in the UI dropdown on next restart.

---

## ADDING A NEW TEMPLATE

Edit `backend/stylegan_engine/templates.py`. Add an entry to `TEMPLATES`:

```python
{
    "id": "tpl_your_id",
    "name": "Template Name",
    "description": "What technique this demonstrates.",
    "model_hint": None,  # or "face", "art" etc to auto-select a model category
    "params": {
        "seed": 0,
        "truncation_psi": 0.7,
        "noise_mode": "const",
        "mix_seed": None,
        "mix_layers": None,
        "layer_weights": None,
        "noise_strength": 1.0,
        "coarse_psi": None,
        "fine_psi": None,
    },
    "style_route": "none",
    "text_prompt": None,
},
```

---

## ADDING A NEW TAURI COMMAND

When you need a new UI → backend action:

**1. Add to `backend/api/server.py`:**
```python
@app.get("/your-endpoint")
async def your_endpoint():
    return {"result": "value"}
```

**2. Add to `src-tauri/src/commands.rs`:**
```rust
#[tauri::command]
pub async fn your_command() -> Result<serde_json::Value, String> {
    let resp = client().get(api("/your-endpoint")).send().await
        .map_err(|e| format!("Request failed: {}", e))?;
    resp.json::<serde_json::Value>().await
        .map_err(|e| format!("Parse error: {}", e))
}
```

**3. Register in `src-tauri/src/main.rs`:**
```rust
.invoke_handler(tauri::generate_handler![
    // ... existing commands ...
    commands::your_command,  // ← add here
])
```

**4. Call from React:**
```typescript
const result = await invoke<YourType>("your_command");
```

---

## INSTALL EVERYTHING FROM SCRATCH

If you ever need to set up the project on a new machine:

```bash
# Clone repo
cd "/Users/tgm/Downloads"

# Clone StyleGAN2 vendor
mkdir -p turrrbo/backend/vendor
git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git turrrbo/backend/vendor/stylegan2

cd turrrbo

# Python environment
python3 -m venv backend/.venv
backend/.venv/bin/pip install torch torchvision
backend/.venv/bin/pip install "numpy<2.0"
backend/.venv/bin/pip install fastapi uvicorn pydantic pillow requests pyinstaller
backend/.venv/bin/pip install git+https://github.com/openai/CLIP.git

# Download model checkpoints
backend/.venv/bin/python3 scripts/download_models.py

# Node dependencies
npm install

# Add missing scripts to package.json
node -e "
const fs = require('fs');
const pkg = JSON.parse(fs.readFileSync('package.json', 'utf8'));
pkg.scripts['backend'] = 'backend/.venv/bin/python3 backend/api/server.py --port 47474';
pkg.scripts['tauri:dev'] = 'concurrently -k -n BACKEND,TAURI -c cyan,yellow \"npm run backend\" \"npm run tauri dev\"';
pkg.scripts['tauri:build'] = 'npm run build && npx tauri build --bundles app';
pkg.scripts['make:dmg'] = 'APP=\"src-tauri/target/release/bundle/macos/TURRRBO.app\" && DMG=\"src-tauri/target/release/bundle/dmg/TURRRBO_0.1.0.dmg\" && mkdir -p src-tauri/target/release/bundle/dmg && STAGING=\$(mktemp -d) && cp -r \"\$APP\" \"\$STAGING/TURRRBO.app\" && ln -s /Applications \"\$STAGING/Applications\" && hdiutil create -volname TURRRBO -srcfolder \"\$STAGING\" -ov -format UDZO \"\$DMG\" && rm -rf \"\$STAGING\" && echo \"Built: \$DMG\"';
pkg.devDependencies['concurrently'] = '^8.2.0';
fs.writeFileSync('package.json', JSON.stringify(pkg, null, 2));
console.log('done');
"
npm install

# Run
npm run tauri:dev
```

---

## FILE MAP — WHERE THINGS LIVE

| What you want to change | File |
|---|---|
| UI layout and components | `src/components/` |
| Global state / store | `src/store/generatorStore.ts` |
| Styles | `src/styles/app.css` |
| Keyboard shortcuts | `src/App.tsx` |
| Tauri commands (Rust) | `src-tauri/src/commands.rs` |
| App entry / sidecar launch | `src-tauri/src/main.rs` |
| Sidecar health polling | `src-tauri/src/sidecar.rs` |
| Tauri config / bundle settings | `src-tauri/tauri.conf.json` |
| Rust dependencies | `src-tauri/Cargo.toml` |
| FastAPI routes | `backend/api/server.py` |
| StyleGAN inference | `backend/stylegan_engine/inference.py` |
| Model catalog | `backend/stylegan_engine/model_registry.py` |
| Style routes | `backend/stylegan_engine/style_routes.py` |
| Templates | `backend/stylegan_engine/templates.py` |
| Preset save/load | `backend/stylegan_engine/preset_store.py` |
| PyInstaller bundle config | `backend/turrrbo_backend.spec` |
| Model metadata | `backend/models/<model_id>/model_card.json` |
| Model download script | `scripts/download_models.py` |
| Node scripts | `package.json` |

---

## QUICK REFERENCE — COMMANDS

```bash
# Run in dev
npm run tauri:dev

# Build app only
npm run tauri:build

# Build DMG only (after tauri:build)
npm run make:dmg

# Kill backend if port stuck
kill $(lsof -ti:47474) 2>/dev/null || true

# Download all models
backend/.venv/bin/python3 scripts/download_models.py

# Download one model
backend/.venv/bin/python3 scripts/download_models.py --models ffhq_1024

# Install a Python package into the venv
backend/.venv/bin/pip install <package>

# Check if a fix is in a file
grep -n "search_term" backend/stylegan_engine/inference.py

# Run backend standalone (for debugging)
backend/.venv/bin/python3 backend/api/server.py --port 47474

# Check backend health
curl http://127.0.0.1:47474/health

# See what's running on the backend port
lsof -i:47474

# Run the bundled app from terminal (see backend logs)
/Applications/TURRRBO.app/Contents/MacOS/TURRRBO
```


Add models

```
for model_dir in backend/models/*/; do
    model_name=$(basename "$model_dir")
    mkdir -p "src-tauri/resources/models/$model_name"
    cp "$model_dir"model_card.json "src-tauri/resources/models/$model_name/"
    for pkl in "$model_dir"*.pkl; do
        [ -f "$pkl" ] && cp "$pkl" "src-tauri/resources/models/$model_name/"
    done
    echo "staged: $model_name"
done
```