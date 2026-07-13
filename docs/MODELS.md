# Model Catalog

The models currently wired into `scripts/download_models.py` and shipped in the
catalog. Each is a pretrained StyleGAN2-ADA checkpoint generating images purely
from latent space — there is no text or image conditioning, so output is governed
by **seed** (which point in latent space) and **truncation ψ** (how far from the
average).

> **License:** all weights below are NVIDIA pretrained checkpoints under the
> **non-commercial research license**. Record the source in each model's
> `provenance` field.

---

## At a glance

| id | Display name | Dataset | Res | Category | Specializes in |
|---|---|---|---|---|---|
| `ffhq_1024` | Synthetic Portraits | FFHQ | 1024 | face | Photorealistic human faces |
| `metfaces_1024` | Museum Wreckage | MetFaces | 1024 | art | Painted / sculpted fine-art portraits |
| `lsun_churches_256` | Haunted Schematics | LSUN Churches | 256 | architecture | Ecclesiastical / gothic building forms |
| `afhq_cats_512` | Animal Forms | AFHQ (cats) | 512 | animal | Feline faces and fur detail |
| `lsun_cars_512` | Automotive Drift | LSUN Cars | 512 | object | Vehicle bodies and silhouettes |

---

## `ffhq_1024` — "Synthetic Portraits"

- **Dataset:** FFHQ (Flickr-Faces-HQ), 1024×1024.
- **Generates:** highly photorealistic, roughly front-facing human faces across a
  broad demographic range, with realistic skin, hair, and background bokeh.
- **Best at:** lifelike portrait synthesis, identity exploration, and smooth
  face-to-face interpolation. The cleanest, most coherent model in the catalog.
- **Notes:** highest resolution and the most "predictable" latent space — a good
  default for demoing seed and interpolation behavior. Lower ψ stays close to an
  average face; higher ψ pushes toward unusual but still face-like results.

## `metfaces_1024` — "Museum Wreckage"

- **Dataset:** MetFaces (faces from artworks in the Metropolitan Museum of Art),
  1024×1024.
- **Generates:** painterly and sculptural portrait faces — brushstroke texture,
  canvas grain, period-painting palettes, occasional statue-like renderings.
- **Best at:** fine-art portraiture and dreamlike, historical-painting
  aesthetics. The artistic counterpart to `ffhq_1024`.
- **Notes:** smaller, more stylized training distribution than FFHQ, so results
  are more uneven and "wrecked" at higher ψ — which is much of the appeal.

## `lsun_churches_256` — "Haunted Schematics"

- **Dataset:** LSUN Outdoor Churches, 256×256.
- **Generates:** cathedral and church facades — spires, towers, arches, rooflines
  against sky.
- **Best at:** architectural and gothic structural compositions. The lowest
  resolution in the set, which lends an abstract, sketch-like quality that suits
  the "schematic" framing.
- **Notes:** architecture rather than a centered subject, so seeds vary more
  wildly in composition than the face models. Expect dreamlike, sometimes
  impossible structures at higher ψ.

## `afhq_cats_512` — "Animal Forms"

- **Dataset:** AFHQ (Animal Faces-HQ), cats subset, 512×512.
- **Generates:** close-up feline faces with detailed fur, eyes, and markings.
- **Best at:** creature/animal exploration and texture-rich fur detail.
- **Notes:** centered-subject model like the face checkpoints, so interpolation
  between seeds is smooth and legible. A good contrast piece to the human-face
  models.

## `lsun_cars_512` — "Automotive Drift"

- **Dataset:** LSUN Cars, 512×512.
- **Generates:** car bodies and vehicle silhouettes from varied angles, usually
  three-quarter views.
- **Best at:** automotive and industrial-object forms — body shapes, reflections,
  and stance.
- **Notes:** object (not face) distribution, so composition and orientation shift
  noticeably between seeds. Higher ψ yields exaggerated, concept-car-like forms.

---

## Verifying against the actual cards

The display names, datasets, resolutions, and categories above reflect the
catalog as wired into `download_models.py`. The per-model `recommended_psi` and
`tags` live in each `backend/models/<id>/model_card.json` — treat those files as
the source of truth and reconcile this doc against them if they've drifted. See
[`ADDING_MODELS.md`](./ADDING_MODELS.md) for the full card schema.
