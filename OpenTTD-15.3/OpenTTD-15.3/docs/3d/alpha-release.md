# Windows alpha packaging and acceptance

9.5g was accepted by the user on 2026-10-20. Alpha preparation adds runtime
packaging and build identification; native interaction acceptance remains open.

## Build and package

Use the configured x64 MSVC build described in [build_and_test.md](build_and_test.md).
From the workspace root, run:

```powershell
python tools/package-alpha.py --label 3d-alpha1
```

For a local preview of uncommitted work:

```powershell
python tools/package-alpha.py --label 3d-alpha1-preview --allow-dirty
```

The tool configures the version label, builds with the two-compiler-worker cap,
runs CTest, stages matching data and DLLs, and writes a game ZIP and a separate
source ZIP under `build/releases`. Existing output directories are never replaced.
Public packages require a clean committed checkout. Local previews identify
modified source with `-m<hash>`; clean builds use `-g<hash>`.

The automatic version finder now handles this workspace's enclosing Git root.
An optional CMake setting `-DOPENTTD_3D_VERSION=3d-alpha1` supplies a readable
label. The compiled version includes the revision in the game and Windows file
properties. Exported sources use `.ottdrev` so rebuilding needs no Git history.
This changes build identification, not simulation, save formats or network rules.

The package copies Release x64 Microsoft CRT DLLs from Visual Studio's REDIST
directory beside the executable. It never copies system DLLs from System32.
Windows supplies the Universal CRT on Windows 10 and later. See Microsoft's
[deployment guidance](https://learn.microsoft.com/en-us/cpp/windows/determining-which-dlls-to-redistribute).
Private copies are maintained by updating the game package. The central Visual
C++ Redistributable installer is an alternative for a future installer release.

The current dependency path still uses this machine's configured Miniconda
LZMA/zlib libraries. Their runtime DLLs and notices are packaged. This is not yet
a fully reproducible dependency build; the checked-in vcpkg manifest is pinned,
and switching to that dependency route needs its own build and verification.

## Download contents

Players receive the executable, matching languages/base data/scripts, runtime
DLLs, unchanged OpenGFX archive, launcher, initial profile, notices, build manifest
and short instructions. There are no personal saves, profiles, development logs,
build trees or Git history in the game ZIP.

The source ZIP contains the game source, CMake inputs, tests, compiled asset
headers, editable Blender originals, exports, textures, asset tools and build
instructions. Cached references, preview images and historical screenshot/log
evidence are excluded. File hashes describe the actual packaged source, including
any modified local-preview files. Keep it available beside the corresponding
game ZIP; see [GPLv2 section 3](https://www.gnu.org/licenses/old-licenses/gpl-2.0.en.html).

The source ZIP also contains the matching OpenGFX 7.1 source archive under
`thirdparty-sources/`. The package tool verifies its pinned SHA-256. In the
development workspace, download it once into `.runtime/alpha-dependencies/`, or
pass its location with `--graphics-source`. Official download:
https://cdn.openttd.org/opengfx-releases/7.1/opengfx-7.1-source.tar.xz
No upload or publication is performed by the packaging command.

## Native acceptance checklist

The [rotated-view alpha checks](rotated-alpha-checks.md) record fresh packaged-binary
verification and the expanded construction callback matrix. These establish
scripted coverage; the native statuses below still need physical input.

Run the packaged build using its launcher. Record each result individually;
automated screenshots and the user's 9.5g acceptance do not establish these checks.
Repeat construction at the classic angle and a rotated management angle.

| Check | Required actions | Status |
|---|---|---|
| Picking | Select ground on slopes/coast/foundations; click vehicles and station/town/sign labels | Pending |
| Rail | Drag straight/diagonal rail, build/remove, cancel with Escape and right-click | Pending |
| Other construction | Road, station, depot, signals, bridge, tunnel and terraform, including invalid placement | Pending |
| Camera during tools | Rotate/tilt with a tool active, pan/zoom to map edges, switch 3D/classic; no unintended commands | Pending |
| Windows | Overlap internal windows and confirm clicks are blocked beneath them; resize additional views | Pending |
| Native window | Resize, maximize/restore, minimize/restore and Alt+Tab while paused and running | Pending |
| Scaling | Change game UI scale and move between monitors with different Windows DPI if available | Pending |
| Persistence | Save/reload, restart and verify preferences, play a route, toggle classic/3D | Pending |
| Ride views | Cab/chase remain spectator-only; tunnel/depot/vehicle removal exits behave correctly | Pending |
| Clean machine | Start without Visual Studio, Miniconda or a separately installed VC runtime | Pending |
| Smaller GPU | Check startup, large-map panning, several views and memory use | Pending |

For failures, record the build version, map/save, tool, angle, zoom and scaling,
plus whether classic rendering behaves correctly. Avoid marking an entire
checklist accepted from general positive playtest feedback.
