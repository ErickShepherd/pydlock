# pydlock brand assets

The pydlock mark is a **padlock formed by an ouroboros** — a serpent coiled to
bite its own tail, its body forming the lock and its head resting over the
keyhole. It fuses the three ideas in the name: the **serpent** (Python), the
**padlock** (encryption), and the **closed, sealed loop** of an ouroboros
(a file locked so nothing gets in or out).

## Assets

| File | Description | Use |
| --- | --- | --- |
| [`pydlock-lockup.png`](pydlock-lockup.png) | Mark + `pydlock` wordmark, dark word | **Shipped lockup** — README header on light backgrounds |
| [`pydlock-lockup-dark.png`](pydlock-lockup-dark.png) | Mark + `pydlock` wordmark, cream word | **Shipped lockup** — README header on dark backgrounds |
| [`pydlock-logo.png`](pydlock-logo.png) | Teal serpent + brass hardware on a dark tile | The mark alone — social, or anywhere with its own background |
| [`pydlock-mark-black.png`](pydlock-mark-black.png) | Black mark, transparent background | Light backgrounds, favicon, print |
| [`pydlock-mark-white.png`](pydlock-mark-white.png) | White mark, transparent background | Dark backgrounds, inline on GitHub dark |

The project README header swaps `pydlock-lockup.png` ⇄ `-dark.png` by
`prefers-color-scheme` via `<picture>`. The mark tile reads on both themes; only
the wordmark recolours (dark ink → cream). The wordmark inside is glyph
**outlines** (no font needed to render); it is rasterized into the shipped PNG.

## Palette

| Role | Hex |
| --- | --- |
| Field (tile) | `#0C1310` |
| Serpent | `#158881` |
| Hardware (shackle, keyhole) | `#DB9A30` |

Wordmark type: **Sora SemiBold** (weight 600), SIL Open Font License 1.1
([`sora-600.ttf`](sora-600.ttf) — the OFL text travels embedded in the font's
`name` table, license URL <https://scripts.sil.org/OFL>).

## Notes

These are **raster** assets. Vector (SVG) versions are deferred until
[limner](https://github.com/ErickShepherd/limner) is ready to trace them; the
flat, hard-edged art here is authored to trace cleanly when that lands.

## Regenerating the lockups

`pydlock-logo.png` is the approved raster mark (a flat, hard-edged emblem made by
an image model). `pydlock-mark-black.png` / `-white.png` are its mono silhouettes.
The lockups are composed from the mark tile + the typeset wordmark:

```bash
# deps: fonttools, pillow, numpy, scipy, cairosvg
python3 build_raster_lockup.py            # -> pydlock-lockup{,-dark}.png
```

`build_raster_lockup.py` gives the tile transparent rounded corners, typesets
`pydlock` as vector glyph outlines from `sora-600.ttf`, embeds the mark as raster
in a lockup SVG, and rasterizes light/dark PNGs at 3× the README display width.
