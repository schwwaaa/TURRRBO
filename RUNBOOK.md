# Adding the 5 extra models — runbook

Run everything from the repo root: `/Users/tgm/Documents/SPLASH/TURRRBO`

---

## 0. Fix the venv tooling (one time)

Your venv is Python 3.14 and was moved from `~/Downloads`, so its `pip` script
is broken. Call pip *through python* (this ignores the broken shebang) and
install the two fetch dependencies:

```bash
backend/.venv/bin/python -m pip install requests gdown
```

> Before you ever build the app, rebuild the venv on Python 3.10–3.13 — 3.14
> breaks PyInstaller. For just fetching/converting models, the current venv is fine.

---

## 1. Place these files

```
scripts/fetch_models.py                               # replaces fetch_extra_models.py
backend/models/brecahad_512/model_card.json
backend/models/afhq_wild_512/model_card.json
backend/models/lsun_horse_256/model_card.json
backend/models/trypophobia_1024/model_card.json
backend/models/beetles_1024/model_card.json
```

---

## 2. Fetch everything (self-verifying)

```bash
backend/.venv/bin/python scripts/fetch_models.py
```

This checks each existing file against its true size. The truncated
`afhq_wild_512.pkl` will be detected as invalid and **re-downloaded
automatically**. Output is one line per model: `OK`, `DONE`, or `FAILED`.

- The **three NVIDIA models** (`brecahad_512`, `afhq_wild_512`, `lsun_horse_256`)
  download and verify with no extra steps.
- The **two Google Drive models** (`trypophobia_1024`, `beetles_1024`) may report
  `FAILED` if Drive blocks the automated download — see step 3.

If you ever suspect a file is bad, force a clean re-pull of one model:

```bash
backend/.venv/bin/python scripts/fetch_models.py --only afhq_wild_512 --force
```

---

## 3. Only if the Drive models FAILED in step 2

Google Drive blocks automated downloads of large public files. Open each link in
a browser once (this clears the scan prompt), download the `.pkl`, then convert:

- trypophobia: https://drive.google.com/file/d/12yYXZymadSIj74Yue1Q7RrlbIqrXggo3/view
- beetles:     https://drive.google.com/file/d/1BOluDQSMzKLgJ3tipAD3tfq5p6AEv_-C/view

```bash
backend/.venv/bin/python backend/vendor/stylegan2/legacy.py \
    --source=/path/to/downloaded-trypophobia.pkl \
    --dest=backend/models/trypophobia_1024/trypophobia_1024.pkl
```

(Repeat for beetles with its own dest path.)

---

## 4. Restart the backend

The new models appear in the catalog. Before any distribution build, run:

```bash
npm run stage:models
```

---

## If a model still errors on load ("No such file" / "truncated")

That means a `model_card.json` exists without a valid `.pkl` beside it. Either
re-run step 2 for that model with `--force`, or drop the folder so the registry
stops choking on it:

```bash
rm -rf backend/models/<id>      # e.g. trypophobia_1024
```
