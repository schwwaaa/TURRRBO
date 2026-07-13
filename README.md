# TURRRBO

A desktop image instrument built on StyleGAN2. Generates synthetic images from
latent space — seed exploration, truncation control, and style mixing — packaged
as a native app for artists.

**Non-commercial use only** (due to NVIDIA StyleGAN2 model license).

---

## Stack

| Layer | Technology |
|---|---|
| Desktop shell | Tauri (Rust) |
| Frontend | React + TypeScript + Zustand |
| Backend / inference | Python + FastAPI + StyleGAN2-ADA-PyTorch |
| IPC | Tauri commands → localhost HTTP |

---

## First-time setup

### 1. Install system dependencies

- [Rust](https://rustup.rs/) (stable)
- [Node.js](https://nodejs.org/) 18+
- Python 3.10+
- Tauri CLI prerequisites for your OS: https://tauri.app/v1/guides/getting-started/prerequisites

### 2. Clone StyleGAN2-ADA-PyTorch into vendor

```bash
git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git backend/vendor/stylegan2
```

### 3. Install Python backend deps

```bash
cd backend
pip install -r requirements.txt
```

Install PyTorch separately with the correct platform variant:
```bash
# CUDA 12.1 (NVIDIA GPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Apple Silicon (MPS)
pip install torch torchvision

# CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

### 4. Download pretrained model checkpoints

```bash
python scripts/download_models.py
```

This downloads NVIDIA pretrained weights into `backend/models/*/`.
These files are for **non-commercial use only** per the NVIDIA license.

Available models:
- `ffhq_1024` — Synthetic Portraits (FFHQ, 1024px)
- `metfaces_1024` — Museum Wreckage (MetFaces painting corpus, 1024px)
- `lsun_churches_256` — Haunted Schematics (LSUN Churches, 256px)
- `afhq_cats_512` — Animal Forms (AFHQ cats, 512px)
- `lsun_cars_512` — Automotive Drift (LSUN Cars, 512px)

### 5. Install frontend deps

```bash
npm install
```

---

## Development

Run Tauri in dev mode (starts Python backend automatically as a sidecar):

```bash
npm run tauri dev
```

Or run the Python backend standalone for faster iteration:

```bash
cd backend
python api/server.py --port 47474
```

---

## Building for distribution

### 1. Bundle the Python sidecar

```bash
pip install pyinstaller
python scripts/build_sidecar.py
```

This produces `src-tauri/binaries/python-sidecar-<target-triple>`.

### 2. Build the Tauri app

```bash
npm run tauri build
```

Outputs a `.dmg` (macOS) or `.msi` / `.exe` (Windows) installer in `src-tauri/target/release/bundle/`.

---

## Project structure

```
turrrbo/
  src/                       React frontend
    components/
      ModelCatalog.tsx       Left rail — model selection
      ParameterControls.tsx  Right rail — StyleGAN controls
      PreviewPanel.tsx       Center — image display + history
      StatusBar.tsx          Footer — backend health
    store/
      generatorStore.ts      Zustand global state
    styles/app.css           All styles
  src-tauri/                 Tauri / Rust shell
    src/
      main.rs                App entry, sidecar launch
      commands.rs            Tauri command handlers (proxy to Python API)
      sidecar.rs             Backend health polling
  backend/                   Python inference service
    api/server.py            FastAPI server (runs on :47474)
    stylegan_engine/
      inference.py           StyleGAN2 wrapper
      model_registry.py      Reads model_card.json files
      preset_store.py        Saves/loads user presets
    models/                  One subfolder per checkpoint
      ffhq_1024/
        model_card.json
        *.pkl                (downloaded separately)
    presets/                 User-saved parameter presets
    vendor/stylegan2/        Cloned from NVlabs (not committed)
  scripts/
    download_models.py       Fetch pretrained checkpoints
    build_sidecar.py         PyInstaller bundle script
  resources/
    licenses/
      THIRD_PARTY_LICENSES.txt
```

---

## StyleGAN controls

| Control | Range | What it does |
|---|---|---|
| **Seed** | 0 – 2³¹ | Selects a point in latent Z space — each seed is a distinct identity |
| **Truncation ψ** | 0.0 – 1.0 | Low = average/safe; high = extreme/unusual. 0.7 is the NVIDIA default |
| **Noise mode** | const / random / none | Controls stochastic surface detail. `const` is deterministic |
| **Mix seed** | optional int | Borrows coarse structure (pose, shape) from a second latent point |

---

## Adding custom model checkpoints

1. Create a folder under `backend/models/<your_model_id>/`
2. Copy your `.pkl` checkpoint into it
3. Write a `model_card.json` — see `backend/models/ffhq_1024/model_card.json` as a template
4. Restart the backend — the model will appear in the catalog automatically

---

## License

TURRRBO application code: personal / non-commercial use.

Pretrained StyleGAN2 weights: NVIDIA non-commercial research license.
See `resources/licenses/THIRD_PARTY_LICENSES.txt` for full attribution.
