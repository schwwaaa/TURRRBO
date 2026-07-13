# Building TURRRBO

This covers everything from a fresh clone to a signed-ready installer. There are
two distinct paths: **development mode** (fast iteration, backend runs from
source) and **distribution builds** (backend is frozen into a sidecar binary and
bundled into the app).

---

## 1. Prerequisites

Install these once per dev machine:

| Tool | Version | Notes |
|---|---|---|
| Rust | stable | via [rustup](https://rustup.rs/) |
| Node.js | 18+ | |
| Python | **3.10 – 3.13** | **Not 3.14** — PyInstaller has known issues with it. The version that matters is the one in `backend/.venv`, not your system Python. |
| Tauri CLI prerequisites | per-OS | See <https://tauri.app/v1/guides/getting-started/prerequisites> (Xcode CLT on macOS; MSVC build tools + WebView2 on Windows). |
| PyInstaller | latest | Only needed for distribution builds. Installed into the venv. |

---

## 2. First-time setup

```bash
# 1. Clone the StyleGAN2-ADA engine into vendor (not committed to our repo)
git clone https://github.com/NVlabs/stylegan2-ada-pytorch.git backend/vendor/stylegan2

# 2. Create the backend virtualenv and install deps
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
```

Install PyTorch separately with the variant that matches the hardware — do **not**
pin it in `requirements.txt`, because the correct wheel differs per machine:

```bash
# Apple Silicon (MPS)
backend/.venv/bin/pip install torch torchvision

# NVIDIA GPU (CUDA 12.1)
backend/.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# CPU only
backend/.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Then pull the model weights and install the frontend:

```bash
# 3. Download pretrained checkpoints into backend/models/*/
backend/.venv/bin/python scripts/download_models.py

# 4. Frontend deps
npm install
```

> A missing `torch` in the venv is the single most common setup failure. See
> [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md#torch-not-found).

---

## 3. Development mode

In dev, the Python backend is launched automatically alongside Tauri (via
`concurrently`). You do **not** need a sidecar binary.

```bash
npm run tauri:dev
```

If you want to iterate on the backend alone (faster restart loop), run it
standalone and point Tauri at `:47474`:

```bash
# macOS / Linux
backend/.venv/bin/python3 backend/api/server.py --port 47474

# Windows
backend\.venv\Scripts\python backend\api\server.py --port 47474
```

> **Cross-platform gotcha:** the `backend` script in `package.json` hard-codes a
> venv path. On macOS it should read `backend/.venv/bin/python3`; on Windows
> `backend\.venv\Scripts\python`. If you move the checkout between platforms,
> update that one script accordingly.

---

## 4. Distribution builds

A distribution build is **two steps**: freeze the backend into a sidecar binary,
then let Tauri bundle the shell + frontend + staged models + sidecar.

### Step 0 — stage the models (required)

The `.pkl` weights live in `backend/models/` but Tauri only packages what's in
`src-tauri/resources/models/`. Staging copies them across:

```bash
npm run stage:models
```

If you skip this, the app builds fine but ships with **zero models**. See
[`ADDING_MODELS.md`](./ADDING_MODELS.md#bundling-into-a-build).

### Step 1 — freeze the Python sidecar

**macOS (Apple Silicon):**

```bash
backend/.venv/bin/python3 -m PyInstaller \
    --clean --noconfirm \
    --distpath "src-tauri/binaries/_dist" \
    --workpath "build/pyinstaller" \
    backend/turrrbo_backend.spec

cp src-tauri/binaries/_dist/turrrbo-backend \
   src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin
chmod +x src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin
```

**Windows (x64):**

```cmd
backend\.venv\Scripts\python -m PyInstaller ^
    --clean --noconfirm ^
    --distpath "src-tauri\binaries\_dist" ^
    --workpath "build\pyinstaller" ^
    backend\turrrbo_backend.spec

copy src-tauri\binaries\_dist\turrrbo-backend.exe ^
     src-tauri\binaries\turrrbo-backend-x86_64-pc-windows-msvc.exe
```

> The binary **must** be renamed to include the target triple
> (`-aarch64-apple-darwin`, `-x86_64-pc-windows-msvc`, etc.). Tauri's
> `externalBin` resolves the sidecar by appending the triple to the base name.
> A mismatch here is a hard build failure — see
> [`TROUBLESHOOTING.md`](./TROUBLESHOOTING.md#sidecar-binary-not-found).

### Step 2 — build the app

```bash
npm run tauri:build
```

**Output locations:**

| Platform | Artifact |
|---|---|
| macOS | `src-tauri/target/release/bundle/macos/TURRRBO.app` (and `.dmg`) |
| Windows (MSI) | `src-tauri/target/release/bundle/msi/TURRRBO_0.1.0_x64_en-US.msi` |
| Windows (NSIS) | `src-tauri/target/release/bundle/nsis/TURRRBO_0.1.0_x64-setup.exe` |

---

## 5. Build order summary

```
download_models.py  →  stage:models  →  PyInstaller (sidecar)  →  tauri:build
   (one-time)           (every build    (every build that         (produces
                         after model     changes backend code)     installer)
                         changes)
```

For a routine release build with no backend or model changes, the sidecar from a
previous build can be reused — only re-run PyInstaller when the Python code or
its dependencies changed.
