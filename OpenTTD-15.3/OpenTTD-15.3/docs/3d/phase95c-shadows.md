# Phase 9.5c: lighting and grounding experiment

Status (2026-10-19): **approved by the user**. Contact shadows are the default; contact and sun shadows remain a menu option, and No shadows stays available.

## What was built

A saved client preference, `gui.renderer_3d_shadows`, set from the 3D toolbar menu (No shadows / Contact shadows / Contact and sun shadows) or `renderer_3d shadows off|contact|sun`.

- **Off** skips every shadow pass. The shader change multiplies by exactly 1, so the original lighting is unchanged.
- **Contact**: after the opaque draw, a copy of the view's depth is used to darken whatever lies at the foot of each static model and vehicle. Each instance contributes one footprint box, drawn from the existing instance streams. Overlaps keep the darkest value (max blend into an R8 buffer, then one multiply), so dense forests do not darken step by step. The maximum darkening is 22%. Effects, hidden or transparent objects, and flat objects under 1.5 units do not cast.
- **Contact and sun**: one 4096² orthographic sun shadow map along the existing fixed light direction, fitted to the view's visible chunks. It is sampled with 4-tap hardware PCF and a normal offset, and removes up to 55% of a face's direct light. Glowing colours (lamps, flames) and selected tiles never darken. Wide orthographic views fade sun shadows out when texels exceed 1.5 world units and skip the pass beyond 3. Cab/chase views draw sun shadows only within 448 world units (28 tiles), fading over the last quarter.
- Shadows reach a few units past what changed, so scoped invalidation widens its change boxes when shadows are on.
- If anything is unsupported (blit, blend equation, programs or framebuffer), shadows stay off and the current lighting remains. Shadows are also off during the GPU reference comparison.

## Visual comparison

`tools/phase95c-shadows.ps1 -Scene infrastructure|town|fleet` captures each view paused in one run, once per mode. `tools/verify-phase95c-shadows.py` checks them and writes [sheets](evidence/phase9/p5c/) (top: off, middle: contact, bottom: sun) with [numbers](evidence/phase9/p5c/visual-results.json). **12 views pass**: no pixel gets lighter, contact stays under 3 levels mean darkening and no GL or shadow failures are logged.

| Views | Contact: pixels changed / mean darkening | Contact and sun |
|---|---:|---:|
| Infrastructure (slopes, bridge, forest), classic, close and two rotated angles | 10–20% / 1.0–2.1 | 23–37% / 3.0–5.2 |
| Dense town, classic, close, rotated | 18–19% / 1.9–2.1 | 28–29% / 3.9–4.4 |
| Town street (enlarged still view) | 7.5% / 0.8 | 10.5% / 1.3 |
| Fleet, 4 windows: normal, chase, cab | 7–11% / 0.7–1.1 | 20–23% / 2.8–3.1 |
| Far zoom-out | 0.9% / 0.1 | 1.7% / 0.2 |

The first contact version (multiplied overlaps, 30%) averaged 4.2 levels and darkened forest floors heavily. It was replaced before these captures. Track, signals and company colours remain readable in all sheets.

## Cost

These were measured with `tools/phase9-performance.ps1 -Shadows off|contact|sun` (the 9.6 fleet cases, 1920×1080, LOD off, 15 s after a 5 s warm-up).

**Caveat:** the machine was running two other game editors throughout, which the user could not stop. Some single runs spiked several-fold, for example one Off run at 61 ms work. The table therefore uses back-to-back Off/Contact/Sun runs and quotes the typical value, and outliers are excluded. Treat differences under about 0.3 ms as noise. The draw/work values are CPU; GPU is the timer-query mean per drawing tick.

| Case | Off draw / work / GPU | Contact | Contact and sun |
|---|---:|---:|---:|
| No vehicle windows | 1.56 / 1.26 / 0.19 ms | 1.70 / 1.37 / 0.22 | 1.81 / 1.35 / 0.46 |
| 4 ordinary windows | 3.02 / 1.63 / 0.19 | 3.25–3.40 / 1.66–1.72 / 0.30 | 3.59–3.73 / 1.74–1.91 / 1.11 |
| 4 mixed cab/chase | 4.59–4.70 / 6.69–6.86 / 1.01–1.15 | 5.08–5.38 / 7.24–7.61 / 1.19 | 5.41 / 7.78 / 2.46 * |
| 1 enlarged chase | 1.88–2.31 / 3.87–4.47 / 0.41 | 2.05 / 4.10 / 1.47 | 2.54 / 5.04 / 0.86 * |
| 4 enlarged mixed | 4.51 / 6.70 / 1.06 | 5.68–6.28 / 8.01–8.66 / 1.44 | 6.16 / 8.71 / 2.61 * |

\* After the 448-unit sun range. Before it, sun shadows covered the full 64-tile draw distance: an enlarged chase view cost +4.3 ms draw / +8 ms work, and four enlarged views reached 12 ms draw / 17 ms work (p95 frame 27 ms).

Memory: sun shadow map 64 MiB of GPU memory, allocated on first use of sun shadows; contact depth and occlusion copies take 5 bytes per pixel of the largest view (10 MiB at 1920×1080, about 40 MiB at 4K). Process working set did not change measurably (within run-to-run noise).

## Recommendation

- **Contact shadows: accepted as the default** (user decision, 2026-10-19). It is subtle, works in every view and costs a few tenths of a millisecond in most cases, up to about 1 ms with four cab/chase windows.
- **Contact and sun shadows: optional.** They look good and are now affordable with the range limit, but they add 1–2 ms with several cab/chase windows and 64 MiB of GPU memory.
- Neither mode is rejected; Off remains available. LOD stays off.

## Verification

- Release builds; 123/123 tests pass.
- Visual: 12 views in 3 modes pass `verify-phase95c-shadows.py`.
- Performance: 8 cases × 3 modes, plus 30 interleaved runs and 6 runs after the range limit, all pass `verify-phase9-performance.py`.
- Not exercised: native mouse use of the menu items (as with 9.5a, the computer-use tool is unavailable); the scripted path sets the same saved setting.
