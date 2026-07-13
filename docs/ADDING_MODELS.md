# Adding New Models

Adding a model is a **drop-in operation** — no code changes required. On startup,
`backend/stylegan_engine/model_registry.py` scans `backend/models/` and registers
every folder that contains a valid `model_card.json`.

---

## 1. Folder layout

Each model is one folder under `backend/models/`, containing exactly two things:

```
backend/models/
  your_model_name/
    model_card.json      ← metadata
    your_model.pkl       ← the StyleGAN2 checkpoint
```

The folder name **is** the model id (see the `id` field below — they must match).

---

## 2. `model_card.json` schema

```json
{
  "id": "your_model_name",
  "name": "Display Name",
  "description": "Shown under the name when the model is selected.",
  "resolution": 512,
  "category": "art",
  "provenance": "Training source, license, URL.",
  "checkpoint_file": "your_model.pkl",
  "recommended_psi": 0.7,
  "tags": ["portrait", "abstract"]
}
```

| Field | Type | Purpose |
|---|---|---|
| `id` | string | Internal identifier used everywhere. **Must exactly match the folder name.** |
| `name` | string | Display name in the catalog left-rail. |
| `description` | string | Sub-line shown when the model is selected. |
| `resolution` | int | Native output resolution in px (e.g. 256, 512, 1024). Must match the checkpoint. |
| `category` | string | Groups the model in the catalog. One of `face`, `art`, `architecture`, `animal`, `object`, `abstract`, `texture`, or a custom string. |
| `provenance` | string | Training source + license + URL. **Required for third-party weights** — drives the non-commercial attribution. |
| `checkpoint_file` | string | Filename of the `.pkl`, **relative to this model's own folder** (not a full path). |
| `recommended_psi` | float | Truncation ψ auto-loaded when the model is selected. Lower (~0.5) for stable models, higher (~0.8) for chaotic ones. |
| `tags` | string[] | Free-form search/filter tags. |

### The two fields that bite

1. **`id` must equal the folder name.** It's used as the internal key throughout
   the registry, the frontend store, and the API. A mismatch makes the model
   silently fail to resolve.
2. **`checkpoint_file` is just a filename**, resolved relative to the model
   folder — not an absolute or repo-relative path.

---

## 3. Dev workflow

```bash
# 1. Create the folder + drop in the .pkl and model_card.json
# 2. Restart the backend so the registry re-scans
backend/.venv/bin/python3 backend/api/server.py --port 47474
```

That's it for development. The model appears in the catalog on next launch.

---

## 4. Bundling into a build

This is the step that's easy to forget. The `.pkl` files in `backend/models/`
are **not** pulled into a packaged build automatically — Tauri only bundles what
lives in `src-tauri/resources/models/`. They must be staged first:

```bash
npm run stage:models     # runs scripts/stage_models.js
```

`stage_models.js` is a Node script (cross-platform — works identically on macOS
and Windows) that copies each model folder from `backend/models/` into
`src-tauri/resources/models/`. Run it **before** `npm run tauri:build` any time
you add or change a model.

> If a new model works in `npm run tauri:dev` but is missing from the built
> `.app`/`.msi`, you forgot `stage:models`. This is the #1 "where did my model
> go" cause.

---

## 5. Where the weights come from

- **Pretrained NVIDIA checkpoints** (FFHQ, MetFaces, AFHQ, LSUN, etc.) — already
  wired into `scripts/download_models.py`. To add another NVIDIA checkpoint,
  extend that script and write the matching `model_card.json`. These are
  **non-commercial** — set `provenance` accordingly.
- **Self-trained checkpoints** — any StyleGAN2-ADA `.pkl` from your own training
  run works. The license is then yours; record that in `provenance`.

Either way the resolution in the card must match what the checkpoint was trained
at, or inference will error on the first generate.
