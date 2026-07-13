"""
backend/stylegan_engine/inference.py
StyleGAN2-ADA-PyTorch inference engine.
Uses the repo's own legacy.load_network_pkl() which handles both
TF-format (old StyleGAN2) and PyTorch-format (ADA) checkpoints.
"""

import sys
import os
from pathlib import Path
from typing import Optional, List

import numpy as np
import torch
import PIL.Image

VENDOR_DIR = Path(__file__).parent.parent / "vendor" / "stylegan2"
if VENDOR_DIR.exists() and str(VENDOR_DIR) not in sys.path:
    sys.path.insert(0, str(VENDOR_DIR))


class StyleGANEngine:
    def __init__(self):
        self._G = None
        self.current_model_id: Optional[str] = None
        self._device = self._resolve_device()
        print(f"[StyleGANEngine] device: {self._device}")

    @staticmethod
    def _resolve_device() -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def load_model(self, model_info):
        model_id = model_info["id"] if isinstance(model_info, dict) else model_info.id
        checkpoint = model_info["checkpoint_file"] if isinstance(model_info, dict) else model_info.checkpoint_file

        if self.current_model_id == model_id and self._G is not None:
            return

        print(f"[StyleGANEngine] loading '{model_id}' from {checkpoint}")

        import inspect as _inspect
        import dnnlib
        import legacy

        # Patch inspect.getsource — old TF-format checkpoints (churches, cars)
        # call getsource() on TF graph ops which raises OSError.
        _orig_getsource = _inspect.getsource
        def _safe_getsource(obj, **kwargs):
            try:
                return _orig_getsource(obj, **kwargs)
            except (OSError, TypeError):
                return ""
        _inspect.getsource = _safe_getsource

        # Detect checkpoint format by reading the first two bytes.
        # ADA-format (FFHQ, MetFaces, Cats) are gzip-compressed: magic bytes 1f 8b
        # TF-format (Churches, Cars) are plain pickle: no gzip header
        with open(checkpoint, "rb") as _f:
            _magic = _f.read(2)
        _is_gzip = (_magic == b"\x1f\x8b")

        try:
            if _is_gzip:
                # ADA checkpoint — use dnnlib open_url which handles gzip
                print(f"[StyleGANEngine] detected ADA format (gzip), using open_url")
                with dnnlib.util.open_url(checkpoint) as f:
                    data = legacy.load_network_pkl(f)
            else:
                # TF checkpoint — plain pickle, open directly
                print(f"[StyleGANEngine] detected TF format (plain pickle), using direct open")
                with open(checkpoint, "rb") as f:
                    data = legacy.load_network_pkl(f)
        except Exception as exc:
            _inspect.getsource = _orig_getsource
            raise RuntimeError(f"Failed to load '{checkpoint}': {exc}") from exc

        _inspect.getsource = _orig_getsource

        G = data.get("G_ema", data.get("G"))
        if G is None:
            raise ValueError(f"No generator found in checkpoint. Keys: {list(data.keys())}")

        # MPS doesn't support float64 — cast everything to float32
        self._G = G.eval().float().to(self._device)
        self.current_model_id = model_id
        print(f"[StyleGANEngine] loaded '{model_id}' — res: {G.img_resolution}, z_dim: {G.z_dim}")

    def _seed_to_z(self, seed: int) -> torch.Tensor:
        rng = np.random.RandomState(seed)
        z = rng.randn(1, self._G.z_dim).astype(np.float32)
        return torch.from_numpy(z).to(self._device)

    def _z_to_w(self, z: torch.Tensor, truncation_psi: float) -> torch.Tensor:
        label = torch.zeros([1, self._G.c_dim], device=self._device)
        return self._G.mapping(z, label, truncation_psi=truncation_psi)

    def get_layer_count(self) -> int:
        """Return number of W layers for the loaded model."""
        if self._G is None:
            return 18
        return self._G.num_ws

    @torch.no_grad()
    def generate(
        self,
        seed: int,
        truncation_psi: float,
        noise_mode: str,
        output_path: str,
        preview_path: str,
        mix_seed: Optional[int] = None,
        mix_layers: Optional[List[int]] = None,
        layer_weights: Optional[List[float]] = None,   # per-layer influence 0.0–2.0
        noise_strength: float = 1.0,                   # global stochastic noise scale
        coarse_psi: Optional[float] = None,            # override psi for coarse layers 0-3
        fine_psi: Optional[float] = None,              # override psi for fine layers 8+
    ):
        if self._G is None:
            raise RuntimeError("No model loaded.")

        num_ws = self._G.num_ws

        # Build primary W
        z = self._seed_to_z(seed)
        label = torch.zeros([1, self._G.c_dim], device=self._device)
        w = self._G.mapping(z, label, truncation_psi=truncation_psi)

        # Per-section truncation override
        if coarse_psi is not None or fine_psi is not None:
            w_avg = self._G.mapping.w_avg
            for i in range(num_ws):
                if i < 4 and coarse_psi is not None:
                    w[0, i] = w_avg + (w[0, i] - w_avg) * coarse_psi
                elif i >= 8 and fine_psi is not None:
                    w[0, i] = w_avg + (w[0, i] - w_avg) * fine_psi

        # Style mixing
        if mix_seed is not None:
            z2 = self._seed_to_z(mix_seed)
            w2 = self._G.mapping(z2, label, truncation_psi=truncation_psi)
            layers = mix_layers if mix_layers else list(range(4))
            for i in layers:
                if i < num_ws:
                    w[:, i, :] = w2[:, i, :]

        # Per-layer weights — scale deviation from w_avg
        if layer_weights:
            w_avg = self._G.mapping.w_avg
            for i, weight in enumerate(layer_weights[:num_ws]):
                if weight != 1.0:
                    w[0, i] = w_avg + (w[0, i] - w_avg) * weight

        # Synthesize
        img = self._G.synthesis(w, noise_mode=noise_mode)

        # Apply noise strength (post-synthesis brightness/contrast scaling as proxy)
        if noise_strength != 1.0:
            img = img * noise_strength

        img_np = (img.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255)
        img_np = img_np[0].to(torch.uint8).cpu().numpy()
        img_pil = PIL.Image.fromarray(img_np, "RGB")

        img_pil.save(output_path, "PNG")

        # 512px preview
        w, h = img_pil.size
        scale = 512 / max(w, h)
        img_pil.resize((int(w * scale), int(h * scale)), PIL.Image.LANCZOS).save(preview_path, "PNG")

        print(f"[StyleGANEngine] wrote {output_path}")

    @torch.enable_grad()
    def generate_clip_guided(
        self,
        text_prompt: str,
        truncation_psi: float,
        noise_mode: str,
        output_path: str,
        preview_path: str,
        seed: int = 0,
        steps: int = 100,
        lr: float = 0.05,
        clip_weight: float = 1.0,
    ):
        """
        CLIP-guided generation: optimizes Z to match a text prompt.
        Requires: pip install git+https://github.com/openai/CLIP.git
        """
        try:
            import clip
        except ImportError:
            raise RuntimeError(
                "CLIP not installed. Run: backend/.venv/bin/pip install git+https://github.com/openai/CLIP.git"
            )

        if self._G is None:
            raise RuntimeError("No model loaded.")

        # CLIP runs on CPU or CUDA — not MPS (limited support)
        clip_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        clip_model, clip_preprocess = clip.load("ViT-B/32", device=clip_device)
        clip_model.eval()

        # Encode text
        text_tokens = clip.tokenize([text_prompt]).to(clip_device)
        with torch.no_grad():
            text_features = clip_model.encode_text(text_tokens).float()
            text_features = text_features / text_features.norm(dim=-1, keepdim=True)

        # Initialize Z from seed, make it trainable
        rng = np.random.RandomState(seed)
        z_init = rng.randn(1, self._G.z_dim).astype(np.float32)
        z = torch.from_numpy(z_init).to(self._device).requires_grad_(True)

        optimizer = torch.optim.Adam([z], lr=lr)
        label = torch.zeros([1, self._G.c_dim], device=self._device)

        print(f"[CLIP] optimizing for: '{text_prompt}' — {steps} steps")

        for step in range(steps):
            optimizer.zero_grad()

            w = self._G.mapping(z, label, truncation_psi=truncation_psi)
            img = self._G.synthesis(w, noise_mode=noise_mode)

            # Resize to 224x224 for CLIP
            img_224 = torch.nn.functional.interpolate(
                img, size=(224, 224), mode="bilinear", align_corners=False
            )

            # Normalize for CLIP
            mean = torch.tensor([0.48145466, 0.4578275, 0.40821073], device=self._device).view(1, 3, 1, 1)
            std  = torch.tensor([0.26862954, 0.26130258, 0.27577711], device=self._device).view(1, 3, 1, 1)
            img_norm = (img_224 * 0.5 + 0.5 - mean) / std

            # Move to CLIP device for encoding
            img_clip = img_norm.to(clip_device)
            image_features = clip_model.encode_image(img_clip).float()
            image_features = image_features / image_features.norm(dim=-1, keepdim=True)

            # Maximize cosine similarity
            loss = -clip_weight * (text_features * image_features).sum()
            loss.backward()
            optimizer.step()

            if step % 20 == 0:
                print(f"[CLIP] step {step}/{steps} loss={loss.item():.4f}")

        # Final render
        with torch.no_grad():
            w_final = self._G.mapping(z, label, truncation_psi=truncation_psi)
            img_final = self._G.synthesis(w_final, noise_mode=noise_mode)

        img_np = (img_final.permute(0, 2, 3, 1) * 127.5 + 128).clamp(0, 255)
        img_np = img_np[0].to(torch.uint8).cpu().numpy()
        img_pil = PIL.Image.fromarray(img_np, "RGB")
        img_pil.save(output_path, "PNG")

        pw, ph = img_pil.size
        scale = 512 / max(pw, ph)
        img_pil.resize((int(pw * scale), int(ph * scale)), PIL.Image.LANCZOS).save(preview_path, "PNG")
        print(f"[CLIP] done → {output_path}")
