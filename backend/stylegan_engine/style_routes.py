"""
backend/stylegan_engine/style_routes.py

Named style routes — the "prompting" system for TURRRBO.
Each route maps a human-readable artistic intent to concrete parameter adjustments
applied on top of whatever the user has dialed in.

StyleGAN has no text encoder. These routes work by shifting:
  - truncation_psi   (how far from the "average" the output drifts)
  - noise_mode       (surface texture behavior)
  - psi_offset       (added to user's truncation value, clamped 0–1)
  - mix_layer_preset (which layers to borrow if style mixing is active)
  - label            (display name)
  - description      (shown in UI)
"""

STYLE_ROUTES = [
    {
        "id": "none",
        "label": "None",
        "description": "No route applied — raw parameters used as-is.",
        "psi_offset": 0.0,
        "noise_mode_override": None,
        "mix_layer_preset": None,
    },
    {
        "id": "ghost_contour",
        "label": "Ghost Contour",
        "description": "Pushes toward the edge of the model's learned distribution. Structures dissolve into contour-like outlines.",
        "psi_offset": 0.2,
        "noise_mode_override": "random",
        "mix_layer_preset": None,
    },
    {
        "id": "thermal_hallucination",
        "label": "Thermal Hallucination",
        "description": "High truncation with const noise. Produces over-saturated, heatmap-like surface quality.",
        "psi_offset": 0.25,
        "noise_mode_override": "const",
        "mix_layer_preset": None,
    },
    {
        "id": "overexposed_memory",
        "label": "Overexposed Memory",
        "description": "Low truncation — collapses toward the model mean. Faces and forms become archetypal, washed out.",
        "psi_offset": -0.3,
        "noise_mode_override": "const",
        "mix_layer_preset": None,
    },
    {
        "id": "broken_chroma",
        "label": "Broken Chroma",
        "description": "Random noise mode at mid truncation. Surface detail becomes unstable and shifts per generation.",
        "psi_offset": 0.0,
        "noise_mode_override": "random",
        "mix_layer_preset": None,
    },
    {
        "id": "tv_wreckage",
        "label": "TV Wreckage",
        "description": "Maximum truncation push. The model operates outside its comfort zone — expect structural breakdown.",
        "psi_offset": 0.35,
        "noise_mode_override": "random",
        "mix_layer_preset": None,
    },
    {
        "id": "cartoon_corrosion",
        "label": "Cartoon Corrosion",
        "description": "No noise, high psi. Clean but wrong — forms are coherent but the model's seams show.",
        "psi_offset": 0.2,
        "noise_mode_override": "none",
        "mix_layer_preset": None,
    },
    {
        "id": "structure_transplant",
        "label": "Structure Transplant",
        "description": "Activates style mixing on coarse layers (0–3). Requires a mix seed to be set.",
        "psi_offset": 0.0,
        "noise_mode_override": None,
        "mix_layer_preset": [0, 1, 2, 3],
    },
    {
        "id": "fine_transplant",
        "label": "Fine Transplant",
        "description": "Style mixing on fine layers (8–12). Borrows surface texture and color from mix seed, keeps structure.",
        "psi_offset": 0.0,
        "noise_mode_override": None,
        "mix_layer_preset": [8, 9, 10, 11, 12],
    },
]

ROUTES_BY_ID = {r["id"]: r for r in STYLE_ROUTES}


def apply_route(route_id: str, params: dict) -> dict:
    """
    Given a route_id and a params dict, return a new params dict
    with the route's adjustments applied.
    """
    route = ROUTES_BY_ID.get(route_id)
    if not route or route_id == "none":
        return params

    result = dict(params)

    # Shift truncation, clamp to valid range
    result["truncation_psi"] = max(0.0, min(1.0,
        params.get("truncation_psi", 0.7) + route["psi_offset"]
    ))

    # Override noise mode if route specifies one
    if route["noise_mode_override"] is not None:
        result["noise_mode"] = route["noise_mode_override"]

    # Override mix layers if route specifies a preset
    if route["mix_layer_preset"] is not None:
        result["mix_layers"] = route["mix_layer_preset"]

    return result
