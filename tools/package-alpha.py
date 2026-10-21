"""Build a portable Windows alpha and its corresponding source archive.

Uses an already configured MSVC x64 build. No upload, installer, or Git writes.
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path


WORKSPACE = Path(__file__).resolve().parents[1]
SOURCE_REL = Path("OpenTTD-15.3/OpenTTD-15.3")
SOURCE = WORKSPACE / SOURCE_REL
GRAPHICS_SOURCE_NAME = "opengfx-7.1-source.tar.xz"
GRAPHICS_SOURCE_URL = f"https://cdn.openttd.org/opengfx-releases/7.1/{GRAPHICS_SOURCE_NAME}"
GRAPHICS_SOURCE_SHA256 = "5322524ffd854cb65d1a4f156d84a3573c4156d08c3757aafd1b8fa3cda41f5a"


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git(*args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", *args], cwd=WORKSPACE
    ).decode("utf-8").strip()


def cache_values(build):
    return dict(re.findall(r"^([^/#\r\n:][^:\r\n]*):[^=\r\n]*=(.*)$", (build / "CMakeCache.txt").read_text(), re.M))


def source_files():
    """Only project files; never sweep the workspace, build outputs or profiles."""
    names = set(git("ls-files", "-z").split("\0"))
    # Include newly added packaging instructions in a local --allow-dirty preview.
    names.update(git("ls-files", "--others", "--exclude-standard", "-z").split("\0"))
    for name in sorted(names):
        path = Path(name)
        if not name or not (WORKSPACE / path).is_file():
            continue
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".blend1"}:
            continue
        if path.is_relative_to(SOURCE_REL):
            relative = path.relative_to(SOURCE_REL)
            if relative.name == ".ottdrev":
                continue
            if relative.parts[0] == ".github":
                continue
            if relative.parts[:3] == ("docs", "3d", "evidence"):
                continue
            if relative.parts[:3] in {("assets", "3d", "previews"), ("assets", "3d", "reference")}:
                continue
            # Keep source modules, tests, CMake inputs, asset originals and docs.
            yield path
        elif path.parts[:2] == ("tools", "3d_assets") or name in {
            "tools/package-alpha.py", "tools/prepare-release.ps1", "OPENTTD_3D_CODEX_GUIDE.md"
        }:
            yield path


def audit_dependencies(stage, visual_studio):
    tools_version = (visual_studio / "VC/Auxiliary/Build/Microsoft.VCToolsVersion.default.txt").read_text().strip()
    dumpbin = visual_studio / "VC/Tools/MSVC" / tools_version / "bin/Hostx64/x64/dumpbin.exe"
    system = {"kernel32.dll", "user32.dll", "gdi32.dll", "shell32.dll", "ole32.dll", "oleaut32.dll",
              "advapi32.dll", "opengl32.dll", "ws2_32.dll", "winmm.dll", "imm32.dll", "usp10.dll",
              "winhttp.dll", "bcrypt.dll", "ntdll.dll", "version.dll", "rpcrt4.dll"}
    bundled = {path.name.lower() for path in stage.glob("*.dll")}
    dependencies = {}
    for binary in [stage / "openttd.exe", *sorted(stage.glob("*.dll"))]:
        result = subprocess.check_output([str(dumpbin), "/nologo", "/dependents", str(binary)])
        names = re.findall(r"^\s+([A-Za-z0-9_.-]+\.dll)\s*$", result.decode(errors="replace"), re.M | re.I)
        if not names:
            raise RuntimeError(f"Could not inspect DLL imports: {binary}")
        dependencies[binary.name] = names
        for name in names:
            if name.lower() not in bundled | system and not name.lower().startswith(("api-ms-", "ext-ms-")):
                raise RuntimeError(f"Unpackaged dependency: {binary.name} imports {name}")
    return dependencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="3d-alpha1")
    parser.add_argument("--build-directory", type=Path, default=WORKSPACE / "build/baseline")
    parser.add_argument("--output-directory", type=Path, default=WORKSPACE / "build/releases")
    graphics_source_default = WORKSPACE / "thirdparty-sources" / GRAPHICS_SOURCE_NAME
    if not graphics_source_default.exists():
        graphics_source_default = WORKSPACE / ".runtime/alpha-dependencies" / GRAPHICS_SOURCE_NAME
    parser.add_argument("--graphics-source", type=Path, default=graphics_source_default)
    parser.add_argument("--allow-dirty", action="store_true", help="Local preview only; public packages require a clean checkout")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,19}", args.label):
        parser.error("Use a simple version label of at most 20 characters")
    files = list(source_files())
    dirty = bool(git("status", "--porcelain", "--untracked-files=normal"))
    if dirty and not args.allow_dirty:
        parser.error("Commit the release changes first, or use --allow-dirty for a local preview")
    if not args.graphics_source.is_file() or sha256(args.graphics_source) != GRAPHICS_SOURCE_SHA256:
        parser.error(f"Provide the matching OpenGFX source using --graphics-source; download: {GRAPHICS_SOURCE_URL}")
    source_hashes = {path.as_posix(): sha256(WORKSPACE / path) for path in files}

    build = args.build_directory.resolve()
    output = args.output_directory.resolve()
    output.mkdir(parents=True, exist_ok=True)
    cache = cache_values(build)
    if cache.get("CMAKE_GENERATOR_PLATFORM") != "x64":
        parser.error("This packaging command requires the configured MSVC x64 build")
    cmake = cache["CMAKE_COMMAND"]
    ctest = str(Path(cmake).with_name("ctest.exe"))
    visual_studio = Path(cache["CMAKE_GENERATOR_INSTANCE"])
    redist_version = (visual_studio / "VC/Auxiliary/Build/Microsoft.VCRedistVersion.default.txt").read_text().strip()
    crt = visual_studio / "VC/Redist/MSVC" / redist_version / "x64/Microsoft.VC143.CRT"
    for name in ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"):
        if not (crt / name).is_file():
            raise RuntimeError(f"Missing x64 Release redistributable: {crt / name}")

    log = build / f"{args.label}-package.log"
    print(f"Building and testing; log: {log}", flush=True)
    with log.open("w", encoding="utf-8") as stream:
        def run(command):
            stream.write(f"\n{command!r}\n")
            stream.flush()
            subprocess.run(command, cwd=WORKSPACE, stdout=stream, stderr=subprocess.STDOUT, check=True)
        run([cmake, "-S", str(SOURCE), "-B", str(build), f"-DOPENTTD_3D_VERSION={args.label}"])
        run([cmake, "--build", str(build), "--config", "Release", "--parallel", "1", "--",
             "/p:CL_MPCount=2", "/p:MultiProcMaxCount=2", "/nodeReuse:false"])
        run([ctest, "--test-dir", str(build), "-C", "Release", "--output-on-failure"])
        revision_data = (build / "generated/.ottdrev").read_text().strip().split("\t")
        version, _, modified, revision, _, _ = revision_data
        name = f"OpenTTD-{version}-windows-x64"
        stage = output / name
        source_zip = output / f"{name}-source.zip"
        binary_zip = output / f"{name}.zip"
        if any(path.exists() for path in (stage, source_zip, binary_zip)):
            raise RuntimeError(f"Package already exists: {stage}")
        run([cmake, "--install", str(build), "--config", "Release", "--prefix", str(stage)])

    # Match DLLs to the configured link libraries, rather than copying from PATH.
    runtime_directories = {}
    for dll, key in (("zlib.dll", "ZLIB_LIBRARY"), ("liblzma.dll", "LIBLZMA_LIBRARY")):
        runtime = Path(cache[key]).parent.parent / "bin" / dll
        shutil.copy2(runtime, stage / dll)
        runtime_directories[dll] = runtime.parent
    for dll in crt.glob("*.dll"):
        shutil.copy2(dll, stage / dll.name)
    dependencies = audit_dependencies(stage, visual_studio)

    licenses = stage / "licenses"
    licenses.mkdir()
    lzma_prefix = runtime_directories["liblzma.dll"].parent
    for notice in ("COPYING", "COPYING.0BSD"):
        shutil.copy2(lzma_prefix / "share/doc/xz" / notice, licenses / f"xz-{notice}.txt")
    zlib_environment = runtime_directories["zlib.dll"].parents[1]
    metadata = json.loads(next((zlib_environment / "conda-meta").glob("zlib-*.json")).read_text())
    shutil.copy2(Path(metadata["extracted_package_dir"]) / "info/licenses/LICENSE", licenses / "zlib-LICENSE.txt")
    for notice in (SOURCE / "src/3rdparty").rglob("*"):
        if notice.is_file() and any(word in notice.name.lower() for word in ("license", "licensing", "copying", "readme")):
            target = licenses / "3rdparty" / notice.relative_to(SOURCE / "src/3rdparty")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(notice, target)
    (licenses / "Microsoft-runtime.txt").write_text(
        "Microsoft Visual C++ x64 Release runtime, supplied from the Visual Studio REDIST directory.\n"
        "These DLLs remain Microsoft components under the Visual Studio redistribution terms.\n"
        "https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files\n"
        "https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution\n"
        "Private deployment: update this package to update its bundled runtime.\n", encoding="utf-8")

    # Retain the unchanged OpenGFX archive and all its bundled notices.
    graphics = WORKSPACE / ".runtime/baseline/baseset/4f474658-OpenGFX-7.1.tar"
    shutil.copy2(graphics, stage / "baseset" / graphics.name)
    shutil.copy2(SOURCE / "docs/3d/alpha-readme.txt", stage / "START-HERE.txt")
    shutil.copy2(SOURCE / "docs/3d/alpha-release.md", stage / "docs/alpha-release.md")
    (stage / "openttd.cfg").write_text(
        "[gui]\nrenderer_3d = true\nrenderer_3d_shadows = 1\nrefresh_rate = 60\n"
        "renderer_3d_retro = true\nrenderer_3d_pixel_size = 3\n"
        "renderer_3d_retro_colours = false\nrenderer_3d_retro_dither = false\n"
        "[misc]\nlanguage = english.lng\nresolution = 1600,900\nfullscreen = false\n[newgrf]\n", encoding="ascii")
    (stage / "Play OpenTTD 3D.cmd").write_text(
        '@echo off\ncd /d "%~dp0"\nstart "" "%~dp0openttd.exe" -c "%~dp0openttd.cfg" '
        '-X -QQ -I OpenGFX -v win32-opengl -b 32bpp-optimized -s null -m null\n', encoding="ascii")

    # Capture hashes before archiving; a modified preview is never represented
    # as the clean HEAD source. Editable Blender assets are retained.
    if any(sha256(WORKSPACE / path) != source_hashes[path.as_posix()] for path in files):
        raise RuntimeError("Source changed during the build; rerun to package a matching snapshot")
    manifest = {
        "version": version, "revision": revision, "modified": int(modified),
        "local_preview": dirty, "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_archive": source_zip.name,
        "source_files_sha256": source_hashes,
        "runtime_files_sha256": {path.name: sha256(path) for path in sorted(stage.glob("*.dll"))},
        "dll_imports": dependencies,
        "executable_sha256": sha256(stage / "openttd.exe"),
        "graphics_sha256": sha256(graphics),
        "graphics_source": {"url": GRAPHICS_SOURCE_URL, "sha256": GRAPHICS_SOURCE_SHA256},
        "microsoft_redist_directory_version": redist_version,
        "checks": {"ctest": "pass", "clean_machine": "pending", "native_interaction": "pending"},
    }
    with zipfile.ZipFile(source_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(WORKSPACE / path, path.as_posix())
        archive.write(build / "generated/.ottdrev", (SOURCE_REL / ".ottdrev").as_posix())
        archive.write(args.graphics_source, f"thirdparty-sources/{GRAPHICS_SOURCE_NAME}")
        archive.writestr("RELEASE-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    manifest["source_archive_sha256"] = sha256(source_zip)
    # The player manifest stays small; detailed source hashes are in the source archive.
    del manifest["source_files_sha256"]
    (stage / "build-info.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with zipfile.ZipFile(binary_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                archive.write(path, f"{stage.name}/{path.relative_to(stage).as_posix()}")
    for path in (source_zip, binary_zip):
        path.with_suffix(path.suffix + ".sha256").write_text(f"{sha256(path)}  {path.name}\n", encoding="ascii")
        print(f"Created {path} ({path.stat().st_size / 1024**2:.1f} MiB)", flush=True)
    print("Local packaging complete. Clean-machine and native interaction checks remain pending.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Packaging failed: {error}", file=sys.stderr)
        sys.exit(1)
