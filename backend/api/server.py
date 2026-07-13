"""
backend/api/server.py
TURRRBO FastAPI sidecar — StyleGAN2 inference API
"""

import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent.parent))
from stylegan_engine.inference import StyleGANEngine
from stylegan_engine.model_registry import ModelRegistry
from stylegan_engine.preset_store import PresetStore
from stylegan_engine.style_routes import STYLE_ROUTES, apply_route
from stylegan_engine.templates import TEMPLATES

app = FastAPI(title="TURRRBO Backend", version="0.2.0")

BASE_DIR   = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
PRESETS_DIR = BASE_DIR / "presets"
OUTPUT_DIR  = Path.home() / "turrrbo_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

engine       = StyleGANEngine()
registry     = ModelRegistry(MODELS_DIR)
preset_store = PresetStore(PRESETS_DIR)

# ── Models ────────────────────────────────────────────────────────────────────

class StyleGANParams(BaseModel):
    seed: int                       = Field(0, ge=0)
    truncation_psi: float           = Field(0.7, ge=0.0, le=1.5)
    noise_mode: str                 = Field("const")
    mix_seed: Optional[int]         = None
    mix_layers: Optional[List[int]] = None
    # Extended params
    layer_weights: Optional[List[float]] = None   # per-layer W influence, one per layer
    noise_strength: float           = Field(1.0, ge=0.0, le=3.0)
    coarse_psi: Optional[float]     = None        # psi override for coarse layers 0-3
    fine_psi: Optional[float]       = None        # psi override for fine layers 8+

class GenerateRequest(BaseModel):
    model_id: str
    params: StyleGANParams
    style_route: Optional[str]   = "none"
    text_prompt: Optional[str]   = None           # CLIP-guided if set
    clip_steps: int              = Field(80, ge=10, le=300)
    clip_lr: float               = Field(0.05, ge=0.001, le=0.5)
    output_dir: Optional[str]   = None
    session_note: Optional[str] = None

class GenerateResponse(BaseModel):
    ok: bool
    output_image: Optional[str]    = None
    preview_image: Optional[str]   = None
    model_id: str
    run_id: str
    timing_ms: int
    warnings: List[str]            = []
    error: Optional[str]           = None
    effective_params: Optional[dict] = None
    clip_guided: bool              = False

class ModelInfo(BaseModel):
    id: str
    name: str
    description: str
    resolution: int
    category: str
    provenance: str
    checkpoint_file: str
    recommended_psi: float
    tags: List[str]

class Preset(BaseModel):
    id: str
    name: str
    model_id: str
    params: StyleGANParams
    text_prompt: Optional[str] = None
    note: Optional[str]        = None

class BackendStatus(BaseModel):
    healthy: bool
    gpu_available: bool
    device: str
    loaded_model: Optional[str]
    version: str
    clip_available: bool

# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=BackendStatus)
async def health():
    gpu = torch.cuda.is_available()
    device = "cuda" if gpu else ("mps" if torch.backends.mps.is_available() else "cpu")
    try:
        import clip
        clip_ok = True
    except ImportError:
        clip_ok = False
    return BackendStatus(
        healthy=True, gpu_available=gpu, device=device,
        loaded_model=engine.current_model_id, version="0.2.0",
        clip_available=clip_ok,
    )

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    return registry.list_all()

@app.get("/models/{model_id}", response_model=ModelInfo)
async def get_model(model_id: str):
    info = registry.get(model_id)
    if not info:
        raise HTTPException(404, f"Model '{model_id}' not found")
    return info

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest):
    warnings = []
    model_info = registry.get(req.model_id)
    if not model_info:
        return GenerateResponse(ok=False, model_id=req.model_id, run_id="",
                                timing_ms=0, error=f"Unknown model: {req.model_id}")

    # Validate noise_mode
    if req.params.noise_mode not in ("const", "random", "none"):
        warnings.append(f"Unknown noise_mode '{req.params.noise_mode}', using 'const'")
        req.params.noise_mode = "const"

    # Apply style route
    adjusted = apply_route(req.style_route or "none", req.params.dict())
    req.params = StyleGANParams(**adjusted)

    out_dir = Path(req.output_dir) if req.output_dir else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"turrrbo_{int(time.time())}"

    t0 = time.perf_counter()
    try:
        engine.load_model(model_info)
        output_path  = out_dir / f"{run_id}.png"
        preview_path = out_dir / f"{run_id}_preview.png"

        if req.text_prompt and req.text_prompt.strip():
            # CLIP-guided generation
            engine.generate_clip_guided(
                text_prompt    = req.text_prompt.strip(),
                truncation_psi = req.params.truncation_psi,
                noise_mode     = req.params.noise_mode,
                output_path    = str(output_path),
                preview_path   = str(preview_path),
                seed           = req.params.seed,
                steps          = req.clip_steps,
                lr             = req.clip_lr,
            )
            clip_guided = True
        else:
            engine.generate(
                seed           = req.params.seed,
                truncation_psi = req.params.truncation_psi,
                noise_mode     = req.params.noise_mode,
                output_path    = str(output_path),
                preview_path   = str(preview_path),
                mix_seed       = req.params.mix_seed,
                mix_layers     = req.params.mix_layers,
                layer_weights  = req.params.layer_weights,
                noise_strength = req.params.noise_strength,
                coarse_psi     = req.params.coarse_psi,
                fine_psi       = req.params.fine_psi,
            )
            clip_guided = False

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return GenerateResponse(ok=False, model_id=req.model_id, run_id=run_id,
                                timing_ms=int((time.perf_counter()-t0)*1000),
                                error=str(exc))

    timing_ms = int((time.perf_counter() - t0) * 1000)

    if req.session_note:
        (out_dir / f"{run_id}.json").write_text(json.dumps({
            "run_id": run_id, "model_id": req.model_id,
            "params": req.params.dict(), "session_note": req.session_note,
            "text_prompt": req.text_prompt, "timing_ms": timing_ms,
        }, indent=2))

    return GenerateResponse(
        ok=True, output_image=str(output_path), preview_image=str(preview_path),
        model_id=req.model_id, run_id=run_id, timing_ms=timing_ms,
        warnings=warnings, effective_params=req.params.dict(), clip_guided=clip_guided,
    )

@app.get("/style-routes")
async def list_style_routes():
    return STYLE_ROUTES

@app.get("/templates")
async def list_templates():
    return TEMPLATES

@app.get("/models/{model_id}/layer-count")
async def get_layer_count(model_id: str):
    info = registry.get(model_id)
    if not info:
        raise HTTPException(404, "Model not found")
    engine.load_model(info)
    return {"layer_count": engine.get_layer_count()}

@app.get("/presets", response_model=List[Preset])
async def list_presets():
    return preset_store.list_all()

@app.get("/presets/{preset_id}", response_model=Preset)
async def get_preset(preset_id: str):
    p = preset_store.get(preset_id)
    if not p:
        raise HTTPException(404, "Preset not found")
    return p

@app.post("/presets", response_model=Preset)
async def save_preset(preset: Preset):
    return preset_store.save(preset.dict())

@app.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str):
    preset_store.delete(preset_id)
    return {"ok": True}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port",        type=int, default=47474)
    parser.add_argument("--host",        type=str, default="127.0.0.1")
    parser.add_argument("--models-dir",  type=str, default=None,
                        help="Path to models directory (bundled app)")
    parser.add_argument("--presets-dir", type=str, default=None,
                        help="Path to presets directory (bundled app)")
    args = parser.parse_args()

    # Override directories if passed — this is how the bundled app finds its models
    if args.models_dir:
        MODELS_DIR = Path(args.models_dir)
        print(f"[server] models dir override: {MODELS_DIR}")
    if args.presets_dir:
        PRESETS_DIR = Path(args.presets_dir)
        print(f"[server] presets dir override: {PRESETS_DIR}")

    # Reinitialise registry and store with the correct paths
    registry     = ModelRegistry(MODELS_DIR)
    preset_store = PresetStore(PRESETS_DIR)

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")