# Build & Launch Troubleshooting

A catalog of failures we've actually hit, with the fix. Ordered roughly by how
often they come up. Search by the symptom.

---

## `torch` not found

**Symptom**

```
Traceback (most recent call last):
  File ".../backend/api/server.py", line 19, in <module>
    import torch
ModuleNotFoundError: No module named 'torch'
```

**Cause** — PyTorch is intentionally not in `requirements.txt` (the correct wheel
is platform-specific), so a fresh venv has no `torch`. Or you're launching with a
different Python than the venv that has it.

**Fix** — install the right variant into `backend/.venv` and make sure you launch
with that interpreter:

```bash
# Apple Silicon
backend/.venv/bin/pip install torch torchvision
# CUDA 12.1
backend/.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
# CPU
backend/.venv/bin/pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Launch with `backend/.venv/bin/python3`, not bare `python3`.

---

## Sidecar binary not found / Tauri refuses to compile

**Symptom** — `npm run tauri:build` (or `dev`) fails immediately, before any of
your code compiles, complaining about a missing binary referenced in
`externalBin`.

**Cause** — Tauri validates that every `externalBin` entry physically exists at
build time. If you haven't run PyInstaller yet, or the binary isn't renamed with
the correct target triple, the file Tauri expects isn't there.

**Fix (distribution build)** — build the sidecar first, and rename it to include
the target triple:

```
src-tauri/binaries/turrrbo-backend-aarch64-apple-darwin      (macOS Apple Silicon)
src-tauri/binaries/turrrbo-backend-x86_64-pc-windows-msvc.exe (Windows x64)
```

Tauri resolves the sidecar by taking the base name in `externalBin`
(`binaries/turrrbo-backend`) and appending the platform triple automatically.
The file on disk must match.

**Fix (dev only)** — you don't need a sidecar in dev. Remove the `externalBin`
key from `src-tauri/tauri.conf.json` and run the Python backend manually (or via
`npm run tauri:dev`, which launches it with `concurrently`). Re-add `externalBin`
only when packaging.

---

## New model missing from the built app

**Symptom** — a model shows up in `npm run tauri:dev` but is absent from the
packaged `.app` / `.msi` / `.exe`.

**Cause** — the `.pkl` was never staged into `src-tauri/resources/models/`.
Tauri only bundles what's under `resources/`, not what's in `backend/models/`.

**Fix**

```bash
npm run stage:models
npm run tauri:build
```

Always stage before building after adding or changing a model.

---

## PyInstaller fails / sidecar crashes on launch

**Symptom** — PyInstaller errors during the freeze, or the bundled binary exits
immediately at runtime.

**Cause** — Python 3.14 has known incompatibilities with PyInstaller.

**Fix** — use **Python 3.10–3.13** for the venv used to build the sidecar. The
venv's Python version is what matters, not the system Python. Recreate the venv
on a supported version and reinstall deps if needed.

---

## Model fails to resolve / not appearing in the catalog

**Symptom** — a model folder exists but the model doesn't register, or selecting
it errors.

**Causes & fixes**

- `id` in `model_card.json` doesn't match the folder name → make them identical.
- `checkpoint_file` is a path instead of a bare filename → it must be just the
  filename, relative to the model's own folder.
- `resolution` doesn't match the actual checkpoint → inference errors on first
  generate; correct the card to the checkpoint's native resolution.
- Backend wasn't restarted → the registry only scans on startup.

---

## Cross-platform path / launch breakage (macOS ↔ Windows)

**Symptom** — the `backend` npm script or backend launch fails after moving the
checkout between a Mac and a Windows machine.

**Causes & fixes**

- Venv interpreter path differs per OS. The `backend` script in `package.json`
  must use `backend/.venv/bin/python3` on macOS and
  `backend\.venv\Scripts\python` on Windows. Update it for the current platform.
- The sidecar binary needs a `.exe` extension on Windows; the rename step in the
  build differs accordingly (handled in `sidecar.rs` / the build commands).
- Use `node scripts/stage_models.js` (via `npm run stage:models`) rather than any
  bash loop — the Node script is the cross-platform staging path.

---

## Quick triage checklist

1. Does `backend/.venv` have `torch`? (`backend/.venv/bin/python -c "import torch"`)
2. Is the venv Python 3.10–3.13?
3. Did you `npm run stage:models` before `tauri:build`?
4. For a distribution build, does the sidecar binary exist with the correct
   target-triple suffix?
5. For each model: `id` == folder name, `checkpoint_file` is a bare filename,
   `resolution` matches the checkpoint.
