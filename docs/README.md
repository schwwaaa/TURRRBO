# TURRRBO — Internal Documentation

TURRRBO is a standalone desktop application for generating images from
StyleGAN2 latent space, packaged for artists. It ships the inference engine and
model weights *inside* the app — no Python install required on an end user's
machine.

> **Non-commercial use only.** The pretrained StyleGAN2 weights are covered by
> NVIDIA's non-commercial research license. See [`MODELS.md`](./MODELS.md).

## Stack at a glance

| Layer | Technology |
|---|---|
| Desktop shell | Tauri 1.x (Rust) |
| Frontend | React + TypeScript + Zustand |
| Inference backend | Python + FastAPI + StyleGAN2-ADA-PyTorch |
| Dev↔backend IPC | Tauri commands → localhost HTTP on `:47474` |
| Packaged backend | PyInstaller single-file binary (Tauri sidecar) |

## Contents

| Doc | Covers |
|---|---|
| [`BUILDING.md`](./BUILDING.md) | Prerequisites, first-time setup, dev mode, and producing distributable installers on macOS and Windows. |
| [`ADDING_MODELS.md`](./ADDING_MODELS.md) | The drop-in model folder format, the `model_card.json` schema, and how models get bundled into a build. |
| [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md) | Build and launch failures we've actually hit, with fixes. Check here first when a build breaks. |
| [`MODELS.md`](./MODELS.md) | The current model catalog — what each model generates and what it's good at. |

## Repository layout

```
turrrbo/
  src/                       React frontend
    components/
      ModelCatalog.tsx       Left rail — model selection
      ParameterControls.tsx  Right rail — StyleGAN controls
      PreviewPanel.tsx       Center — image display + history
      StatusBar.tsx          Footer — backend health
    store/generatorStore.ts  Zustand global state
    styles/app.css
  src-tauri/                 Tauri / Rust shell
    src/
      main.rs                App entry, sidecar launch
      commands.rs            Tauri command handlers (proxy to Python API)
      sidecar.rs             Backend launch + health polling
    binaries/                PyInstaller sidecar binaries (per target triple)
    resources/
      models/                STAGED .pkl files for packaging (see ADDING_MODELS.md)
      presets/
      licenses/
    tauri.conf.json
  backend/                   Python inference service
    api/server.py            FastAPI server (runs on :47474)
    stylegan_engine/
      inference.py           StyleGAN2 wrapper
      model_registry.py      Scans models/ and reads model_card.json files
      preset_store.py        Saves/loads user presets
    models/                  One subfolder per checkpoint (source of truth)
    presets/
    vendor/stylegan2/        Cloned from NVlabs (NOT committed)
    turrrbo_backend.spec     PyInstaller spec
    .venv/                   Build/dev virtualenv
  scripts/
    download_models.py       Fetch pretrained checkpoints into backend/models/
    stage_models.js          Copy .pkl files into src-tauri/resources/models/
  package.json
```
