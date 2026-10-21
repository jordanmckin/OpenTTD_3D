# Prototype release inventory

The build is a Windows x64 OpenGL prototype based on the supplied OpenTTD 15.3 archive. Exact upstream revision remains unknown. It must not be presented as an official OpenTTD release or as network-compatible with upstream. Same-binary localhost synchronization was tested in Phase 6; other builds were not.

## Build and package inputs

Follow [build_and_test.md](build_and_test.md), including the two-compiler-worker cap. The current local dependency route uses installed Miniconda LZMA/zlib binaries, not pinned release dependencies. A reproducible distributable should build from the checkout's vcpkg manifest with recorded dependency versions and hashes. That reproducibility is not established by this machine's successful incremental build.

For a local staging directory, include `Release/openttd.exe`, its matching `liblzma.dll` and `zlib.dll`, the generated `lang` and `baseset` directories, the source README, COPYING, third-party notices, and these 3D documents. Preserve the build-root directory layout used by the demo. Supply base graphics separately with their license notices; the source's baseset descriptors alone are insufficient. Do not include personal profiles or saves. The demonstration fixtures are under `docs/3d/fixtures` and may be supplied separately.

For distribution, accompany the binary with its exact corresponding source, modifications, procedural generator, generated headers, CMake inputs and build instructions, retaining the GPL text and copyright notices. The source's [COPYING.md](../../COPYING.md) contains GPL version 2, and [README.md](../../README.md) and `src/3rdparty/README.licensing` identify exceptions and third-party components. Audit the actual packaged DLLs and their license notices before distribution. No public release archive has been produced by this phase.

## Assets and provenance

`assets/3d/manifest.json` records GPL-2.0-only original procedural geometry with no third-party models or textures, the generator path and digest. `tools/3d_assets/generate.py`, `assets/3d/library.json`, previews and `src/video/asset3d_generated.h` are the editable/exported pipeline. The runtime meshes are compiled; there are no asynchronous asset loads to benchmark. OpenGFX 7.1 is separate base graphics, copied only into isolated local profiles and not committed into this project. Retain its own notices if redistributing it.

## Compatibility and outstanding acceptance

- 3D requires the opt-in build option, Windows OpenGL and a supported 32/40-bit blitter. Classic rendering remains the fallback.
- Gameplay NewGRF mapping and arbitrary sprite compatibility are deferred. Shared and missing base-game models remain documented in Phase 5/6; Phase 8 owns final art.
- Construction uses the fixed classic camera; rotated/tilted views are orbit views that return to it for building ([camera-orbit.md](camera-orbit.md)).
- Phase 6's native resize, DPI, cursor, drag and overlapping-window checklist is not entirely accepted.
- Optional codecs and old-save support are limited by the local build dependencies described in the build record.
- Performance results apply to this workstation and these fixtures. Phase 8 art and a 512-square operating fleet are measured in [the priority 11 checkpoint](phase7-p11.md); this includes a memory saving and a small CPU tradeoff. Long sessions, other GPUs and general release performance still require acceptance.

This inventory keeps the local demonstration reviewable while recording why it is not yet a general release candidate.

Latest performance handoff (2026-10-19): [retained static instance streams](phase7-streams.md), final Release and 118 passing tests. Preliminary timing gains precede the final duplicate-write cleanup; final visual/timing reruns remain unfinished after the user requested a session wrap-up. This does not close release acceptance.
