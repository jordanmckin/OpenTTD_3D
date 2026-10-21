# Building OpenTTD 3D

To play without compiling, download the Windows x64 game ZIP from [Releases](https://github.com/jordanmckin/OpenTTD_3D/releases). GitHub's **Code > Download ZIP** and the automatic **Source code** release downloads contain source, not a ready-to-play game.

## Project layout

- `OpenTTD-15.3/OpenTTD-15.3/`: modified OpenTTD 15.3, CMake files, tests, documentation, and assets.
- `tools/`: asset generators, development checks, and release packaging.
- `OPENTTD_3D_CODEX_GUIDE.md`: development history and implementation notes.

Keep this layout: the tools use these relative paths. The source includes the current generated model and texture headers, exported models, and editable Blender assets. Blender and Python are not needed for an ordinary game build; they are used to change or regenerate the artwork and run development tools.

Build outputs, local runtime profiles, Python caches, Blender backups, generated asset previews, reference images, and historical screenshot galleries are excluded. Some development reports link to those omitted galleries. Their absence does not prevent building the game.

## Windows build

The 3D renderer currently targets the Windows OpenGL backend. Follow the full [upstream compilation instructions](OpenTTD-15.3/OpenTTD-15.3/COMPILING.md) for prerequisites and dependency details.

Install Visual Studio 2022 with the C++ tools and Windows SDK, CMake, and vcpkg. The project's `vcpkg.json` describes its dependencies. Git is recommended when cloning; Python is needed for the optional packaging script.

From the root of this repository, in a PowerShell terminal with CMake available, configure an x64 Release build. Replace the example vcpkg path with your installation:

```powershell
cmake -S OpenTTD-15.3/OpenTTD-15.3 -B build/baseline `
  -G "Visual Studio 17 2022" -A x64 `
  -DCMAKE_TOOLCHAIN_FILE="C:/vcpkg/scripts/buildsystems/vcpkg.cmake" `
  -DVCPKG_TARGET_TRIPLET=x64-windows-static

cmake --build build/baseline --config Release --parallel 1 -- /p:CL_MPCount=2 /p:MultiProcMaxCount=2 /nodeReuse:false

ctest --test-dir build/baseline -C Release --output-on-failure
```

The executable is `build/baseline/Release/openttd.exe`. Generated language and base-set descriptors are in `build/baseline/lang` and `build/baseline/baseset`. Run the game from the build directory so it can find those files:

```powershell
Push-Location build/baseline
try {
    & ./Release/openttd.exe -v win32-opengl
} finally {
    Pop-Location
}
```

You also need a base graphics set, such as OpenGFX. Install it through the game's content setup, or provide an existing installation as described in the [OpenTTD README](OpenTTD-15.3/OpenTTD-15.3/README.md). The source repository does not include the downloaded OpenGFX runtime archive. Enable 3D with the game's **3D** toolbar menu. A self-built game uses normal OpenTTD user directories unless you configure a separate profile; the release launcher sets up its own portable profile.

The commands above describe a new developer setup. The historical [build record](OpenTTD-15.3/OpenTTD-15.3/docs/3d/build_and_test.md) documents the original author's machine and contains machine-specific paths; adapt those paths if following that record.

## Packaging releases

`tools/package-alpha.py` is the existing Windows maintainer packaging tool. It rebuilds, runs tests, and creates a portable game ZIP and matching source ZIP under `build/releases`. Use a new version label for each release and commit the source changes before creating a public package.

The packager expects the original maintainer's configured MSVC build, including dynamic zlib/LZMA libraries, Visual C++ runtime files, and a locally installed OpenGFX 7.1 archive at `.runtime/baseline/baseset`. It also needs the matching OpenGFX source archive; run `python tools/package-alpha.py --help` for options, and see the script for its expected download URL and checksum. It is not a general packaging command for the static-vcpkg developer build shown above.

Publish the matching source commit before tagging a release. Attach the game ZIP, matching source ZIP, and checksums to GitHub Releases. Keep the full portable game folder inside the game ZIP: players need its data files, libraries, licence notices, and launcher as well as `openttd.exe`.
