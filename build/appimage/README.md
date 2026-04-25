---
short-description: Building a portable AppImage of Pitivi
...

# Pitivi AppImage

A self-contained, portable Pitivi binary that runs on any Linux desktop —
including XFCE, KDE, MATE, LXQt, plain X11, etc. — **without** requiring
the GNOME runtime to be installed on the target system. Everything Pitivi
needs (GTK, GES, GStreamer, Python, codecs, locale data, ~1.7 GB of GNOME
platform) is bundled inside a single ~550 MB executable.

## Quick start

From the repository root:

```
./build/appimage/build.sh
```

This produces `Pitivi-<version>-<arch>.AppImage` in the current directory.
The first run takes a few minutes (it pulls the published Pitivi from
Flathub if it isn't already installed); subsequent runs take ~30 s.

To run the AppImage:

```
./Pitivi-2023.03-x86_64.AppImage
```

If the target host has FUSE 2 installed (most desktops do), the AppImage
mounts itself and launches directly. Otherwise, fall back to:

```
./Pitivi-2023.03-x86_64.AppImage --appimage-extract-and-run
```

## Build script options

```
./build/appimage/build.sh [options]
```

| Option | Effect |
|---|---|
| `--out DIR` | Write the `.AppImage` to `DIR` instead of the current directory. |
| `--keep-appdir` | Keep `_build/AppDir/` for inspection (1.6 GB of hardlinks). |
| `--no-flatpak-install` | Skip `flatpak install`; reuse the already-installed `org.pitivi.Pitivi` (handy for offline builds). |
| `--comp <c>` | squashfs compression: `zstd` (default; only one the modern appimagetool's bundled mksquashfs supports), `xz` / `gzip` (require an external mksquashfs and aren't always available), `none` (debug). |
| `--lean` | Drop bundle bits Pitivi doesn't strictly need (~165 MB saved). See "Size optimisations" below. |
| `-h`, `--help` | Show help. |

### Size optimisations

| Build | Final AppImage | Trade-off |
|---|---|---|
| `--comp zstd` (current default) | ~540 MB | Default since the modern appimagetool only ships zstd. Comparable ratio to xz with much faster decompression. |
| `--comp zstd --lean` | **~390 MB** | See list below. Fully functional Pitivi; only the in-app help viewer is lost. |

`--lean` removes:

- **WebKit + JS engines + libyelp** (~270 MB): Pitivi never imports
  WebKit; the only consumer in the bundle is `libyelp` (the offline
  help viewer). After `--lean` the in-app help opens nothing, but the
  online help on pitivi.org still works.
- **`__pycache__/` directories** (~130 MB): pre-compiled Python
  bytecode. Removed; CPython recreates them on first import. The first
  launch after `--lean` is slightly slower, then identical.
- **Static libs (`*.a`), headers (`include/`), docs (`share/doc`,
  `share/man`, `share/gtk-doc`, `share/devhelp`, `share/info`)** and
  the LibreOffice **`mythes`** thesaurus (~30 MB): never used at runtime.

Environment overrides:

| Variable | Effect |
|---|---|
| `PITIVI_REF` | Bundle a different flatpak ref (default `org.pitivi.Pitivi//stable`). E.g. `PITIVI_REF=org.pitivi.Pitivi//beta`. |
| `PITIVI_HOST_PIXBUF` | Path to the host `libgdk_pixbuf-2.0.so.0` to bundle as overlay (default: auto-detected via `uname -m`). |

## What gets bundled

`build.sh` doesn't compile Pitivi: it pulls the published Flathub artifact
(`org.pitivi.Pitivi`) and the GNOME runtime it depends on, then re-packages
them as an AppImage. Layout inside the AppImage:

```
AppDir/
├── AppRun                  bash entry point — sets env vars, exec's python
├── launcher.py             Python entry point — monkey-patches and boots Pitivi
├── org.pitivi.Pitivi.{desktop,svg}  required by appimagetool
├── app/                    flatpak `/app` tree (Pitivi + its bundled libs)
├── runtime/                flatpak `/usr` tree (GNOME platform 50 base)
├── codecs/                 `org.pitivi.Pitivi.Codecs` extension (optional)
├── host-libs/              host-distro libs that override the runtime's
│                           (currently: libgdk_pixbuf-2.0 sans glycin)
└── wrappers/               shell wrappers prepended to PATH
    └── bwrap               sandbox shim used by libglycin (safety net)
```

## Auto-detection

The build script and the AppImage's `AppRun` together try to discover as
much as possible at runtime so the bundle works on a wide range of hosts
without ever editing files in the hardlinked flatpak tree.

### What `build.sh` discovers automatically

| Item | How | Failure mode |
|---|---|---|
| Architecture | `uname -m` | Aborts on anything other than `x86_64`/`aarch64`. |
| Pitivi deployment path | `flatpak info --user --show-location` | Aborts with a clear message if the flatpak isn't installed. |
| Bundled runtime ref | Parsed from the flatpak's `metadata` (`runtime=…`) | Aborts if the metadata can't be parsed or the runtime isn't installed. |
| Runtime deployment path | `flatpak info --show-location` on the parsed ref | Aborts if not installed. |
| Codecs extension | `flatpak info` on `<id>.Codecs` | Built without codecs if absent (warns with `<none>`). |
| Pitivi version (for the output filename) | `flatpak info \| awk '/Version:/'` | Falls back to `snapshot`. |
| Host `libgdk_pixbuf-2.0.so.0` to overlay | `/usr/lib/$ARCH_TRIPLE/libgdk_pixbuf-2.0.so.0` (overridable via `PITIVI_HOST_PIXBUF`) | Warns and skips the overlay; AppImage will fall back to the runtime's glycin-based loader. |
| Host gdk-pixbuf version | `strings` on the overlaid lib | Warns if older than 2.42 (potential ABI mismatch with bundled GTK). |
| Build tools (`flatpak`, `convert`, `wget`, `find`, `sed`, `install`) | `command -v` | Aborts with a per-tool message naming the package to install. |
| `bwrap` on the build host (optional) | `command -v bwrap` | Warns; only matters because the *target* host needs it for glycin. |
| ImageMagick SVG delegate | `convert -list delegate` | Warns; SVG→PNG fallbacks are skipped, AppImage relies on the target host's librsvg2. |
| Disk space | `df -kP` of `_build/` | Warns below 2 GB free. |
| Python version inside the runtime | `ls $RUNTIME/bin/python3.*` | Aborts if the runtime ships none. |
| `appimagetool` | Cached at `_build/appimagetool`; downloaded on first run | Re-fetched if the cached binary is missing. |

### What `AppRun` discovers at every launch

| Item | How |
|---|---|
| `APPDIR` | `readlink -f $0` (works through symlinks, mounted AppImage, or `--appimage-extract-and-run`). |
| Architecture + matching `ld-linux` filename | `uname -m`. |
| Bundled Python version | `ls $APP/lib/python3.*` (so a runtime bump from python3.13 → 3.14 needs no script change). |
| `gst-plugin-scanner` | App's `libexec` first, runtime's as fallback. |
| `gst-ptp-helper` | Same. |
| `ld-linux` location | `lib64/` first, then `lib/`. |
| Host `gdk-pixbuf` `loaders.cache` | Used if present (`/usr/lib/$ARCH_TRIPLE/gdk-pixbuf-2.0/2.10.0/loaders.cache`). |
| Glycin loader configs | Re-rendered on every launch under `$XDG_CACHE_HOME/pitivi-appimage/glycin-data/` so the `Exec=` line points at the *current* `$APPDIR/runtime/libexec/...`. |

### What `launcher.py` does at import time

| Action | Why |
|---|---|
| Monkey-patches `pitivi.configure.LIBDIR` / `PKGDATADIR`. | The flatpak bakes `/app` into them; we replace them in memory rather than editing the file on disk (it's hardlinked into the user's flatpak install). |
| Re-injects the app's `gi.overrides` directory. | The runtime's PyGObject overrides assume a newer `gi.module` API than the app's older copy ships — we want the app's overrides to win. |
| Wraps `GdkPixbuf.Pixbuf.new_from_file_at_size` with a silent `.svg` → `.png` fallback. | If the target host lacks librsvg2, we transparently load the PNG sibling rendered at build time. |

### What is **not** auto-detected

These are limitations worth being honest about:

- **Target-host glibc version.** The bundled runtime ships glibc 2.42; if
  the target's glibc is much older we route through the runtime's own
  `ld-linux`, but sub-processes spawned by GStreamer still go through the
  host loader. In practice this is fine on any glibc 2.35+ desktop, but
  we don't actively probe.
- **Target-host `bwrap`.** The bundled `bwrap` shim assumes the host has
  bubblewrap installed. If it doesn't, glycin loads silently fail (the
  bundled `libgdk_pixbuf` overlay normally avoids glycin entirely, but
  any code path that goes through `libglycin` directly will fail).
- **Target-host `librsvg2-common`.** Without it, the host
  `loaders.cache` won't have an SVG loader. `launcher.py` falls back to
  pre-rendered PNGs for Pitivi pixmaps; arbitrary SVG assets a user
  drops into a project would still fail to load.
- **Cross-distro libgdk_pixbuf ABI.** We bundle whatever the *build*
  host has. The script warns if it looks older than 2.42, but doesn't
  refuse — verifying ABI compat with the bundled GTK 4.x is left to a
  smoke test.
- **Other libs that may need the same overlay treatment.** Only
  `libgdk_pixbuf` is currently overlaid. Future runtimes may pull in
  more sandboxed delegations (à la glycin) that need similar handling.

## Build host requirements

Hard:

- `flatpak` 1.12+
- ImageMagick (`convert`)
- `wget`
- coreutils, findutils, sed
- ~3 GB free disk during the build
- Filesystem that supports hardlinks across the `_build/` directory and
  the user's `~/.local/share/flatpak/` directory (typically same fs).

Soft:

- `bubblewrap` (only used for the smoke test on the build host; the
  bundled `bwrap` shim invokes whatever `bwrap` is on the *target* host)
- `librsvg2-bin` or any ImageMagick build with an SVG delegate, so
  step 5 of the build can render PNG fallbacks. Without it, the
  AppImage relies on `librsvg2-common` being present on the target.

## Target host compatibility

**The desktop environment doesn't matter.** GNOME, XFCE, KDE, Cinnamon,
MATE, LXQt, Sway, i3 — all work the same way, because the AppImage
bundles its own GTK4 + Adwaita and uses the host's fonts / DBus /
OpenGL drivers (interfaces stable across DEs). What matters is what
the host system provides at the libc / system-library level.

### Hard requirements (AppImage won't start without these)

| Requirement | Minimum | Why |
|---|---|---|
| **Architecture** | `x86_64` or `aarch64` | The only arches we build. |
| **glibc** | 2.35+ (Ubuntu 22.04, Debian 12, Fedora 36+, RHEL 9) | Sub-processes (GStreamer helpers etc.) use the host's `ld-linux`, which then loads the bundled libc 2.42 via `LD_LIBRARY_PATH`. Mismatched versions segfault. |
| **DBus session bus** | running | GTK4 / GIO require it. |
| **X11 or Wayland session** | working | GTK4 needs a display server (XWayland is fine). |
| **OpenGL drivers** | system Mesa or proprietary NVIDIA | We deliberately don't bundle GL extensions (saves ~500 MB and avoids driver mismatches). The video preview won't render without them. |

### Soft requirements (AppImage runs but with degraded features)

| Requirement | If missing |
|---|---|
| **`librsvg2-common`** | Host SVG loading is unavailable. Pitivi's bundled SVG pixmaps are covered by pre-rendered PNG siblings (rendered at build time); arbitrary SVG assets a user drops into a project would fail to load. |
| **`bubblewrap` (`bwrap`)** | Only matters if anything still calls `libglycin` directly. The host `libgdk_pixbuf` overlay normally avoids glycin entirely. |
| **PulseAudio or PipeWire** | No audio. |
| **FUSE 2** | The AppImage can't mount itself; users have to invoke it with `--appimage-extract-and-run` (or extract once via `--appimage-extract`). |
| **Active icon theme that contains `org.pitivi.Pitivi`** | The launcher's `Gtk.IconTheme.load_icon` wrapper falls back to the bundled hicolor icon, so this is purely cosmetic. |

### Distros known to work

| Distro | Status |
|---|---|
| Ubuntu 22.04, 24.04, 25.04 | ✅ tested (build + smoke test) |
| Fedora 38+, including 43 | ✅ tested (after the icon-theme fallback fix) |
| Debian 12 (Bookworm), 13 (Trixie) | ✅ very likely (glibc 2.36+) |
| Linux Mint 21+, Pop!\_OS 22.04+, Manjaro, Arch, EndeavourOS | ✅ very likely |
| openSUSE Tumbleweed, Leap 15.5+ | ✅ likely |
| RHEL/CentOS/Rocky/Alma 9 | ⚠️ glibc 2.34 — at the edge, untested, may work |
| RHEL 8, CentOS 8, Ubuntu 20.04 | ❌ glibc 2.28/2.31, too old |
| Alpine, Void Linux | ❌ musl libc, not glibc |
| Anything ARM-32 (`armhf`) | ❌ not built |

### Self-check before downloading

```
ldd --version | head -1                # need >= 2.35
uname -m                               # need x86_64 or aarch64
ldconfig -p | grep -E 'librsvg|libfuse' | head
```

If glibc ≥ 2.35, arch is x86_64 or aarch64, and `librsvg` + `libfuse`
appear in the output, the AppImage should run.

## How it works

The build doesn't compile Pitivi: it pulls the published Flathub artifact
and re-packages it. Three files do the heavy lifting:

- **`build.sh`** — composes the AppDir by **hardlinking** the deployed
  flatpak trees, layers a host `libgdk_pixbuf` overlay (see below),
  renders PNG fallbacks for SVG pixmaps, and runs `appimagetool`.
- **`AppRun`** — bash entry point. It only sets environment variables
  (`LD_LIBRARY_PATH`, `GI_TYPELIB_PATH`, `GST_PLUGIN_SYSTEM_PATH`,
  `XDG_DATA_DIRS`, `GDK_PIXBUF_MODULE_FILE`, `PYTHONPATH`, …) and execs
  the bundled python via the **runtime's** `ld-linux`. The bundled glibc
  is newer than typical hosts, so the host loader can't load it.
- **`launcher.py`** — Python entry point. Does the filesystem-fragile
  work in memory rather than patching files in the hardlinked tree (see
  the "What `launcher.py` does at import time" table above).

### Why a host `libgdk_pixbuf` overlay?

The GNOME 50 runtime's `libgdk_pixbuf-2.0` is linked against
`libglycin`, which sandboxes every image load in `bwrap`. The sandbox
bind-mounts the host's `/usr` and execs
`/usr/libexec/glycin-loaders/...` — a path that doesn't exist on a
non-GNOME host. We therefore ship the build host's own
`libgdk_pixbuf-2.0.so.0` (without glycin) under `host-libs/` and put it
first on `LD_LIBRARY_PATH`. The shipped lib has to be ABI-compatible
with the runtime's GTK; the build host's gdk-pixbuf is normally fine
(2.42+).

### Why never modify hardlinked files?

`build.sh` hardlinks the user's `~/.local/share/flatpak/` deployment
into `_build/AppDir/`. Editing any hardlinked file via in-place writes
(e.g. `python open(p, 'w')`, `gzip -f`, …) corrupts the user's flatpak
install too. All run-time fixups therefore go through `launcher.py`
monkey-patches; the only files we *create* in the AppDir are net-new
PNG siblings of existing SVGs (which can't collide).

## Files

```
build/appimage/
├── README.md          this file
├── build.sh           main build script
├── AppRun             AppDir entry point (bash)
├── launcher.py        Python entry point (monkey-patches + boot)
├── wrappers/
│   └── bwrap          glycin sandbox shim (safety net)
└── _build/            build artifacts; gitignored
    ├── AppDir/        hardlinked composition (deleted unless --keep-appdir)
    └── appimagetool   cached on first run
```

## Multi-arch status

`x86_64` and `aarch64` are wired in both the build script and the CI
matrix. Other architectures abort upfront. `aarch64` is only useful if
Flathub publishes `org.pitivi.Pitivi/aarch64/stable`; verify with
`flatpak remote-info flathub org.pitivi.Pitivi//stable` before tagging
a release.

## Continuous integration & releases

GitHub Actions workflows under `.github/workflows/`:

- **`ci-appimage.yml`** runs on every PR and push to `master` that
  touches `build/appimage/**`. Builds the full 2×2 matrix (x86_64 ×
  aarch64) × (full × lean) and smoke-tests each AppImage under Xvfb.
  Failures are independent so a broken `--lean` doesn't mask a broken
  `--full`. Artifacts are kept 14 days.
- **`release-appimage.yml`** runs when a tag matching `appimage-v*`
  is pushed (e.g. `appimage-v2023.03.1`). Builds the same matrix and
  publishes a GitHub release with the four AppImages and their
  `.sha256` checksums attached.
- **`_appimage-build.yml`** is the reusable inner workflow both call
  to do the actual build + smoke test for one (arch, variant) cell.

Naming convention for release artifacts:
`Pitivi-<flatpak-version>-<variant>-<arch>.AppImage`.

To cut a release: tag a commit on `master` with `appimage-v*` and push
the tag. CI publishes the release automatically.

## Caveats

- The bundled tree is whatever Flathub currently ships, so the AppImage
  inherits Flathub's release cadence. To bump, run
  `flatpak update --user org.pitivi.Pitivi` and re-run `build.sh`.
- The AppImage is ~540 MB with default zstd compression, or ~390 MB
  with `--lean` (squashfs of a 1.6 GB / 1.2 GB AppDir respectively).
- The bundled GNOME runtime carries its own glibc; sub-processes
  spawned by GStreamer inherit the host loader. On hosts older than the
  runtime's glibc, expect occasional warnings (e.g. `gst-plugin-scanner`
  complaints) — typically benign for the editor itself.
- This is a re-packaging of the Flathub build, not a from-source
  Pitivi build. For a full development setup, see
  [docs/HACKING.md](../../docs/HACKING.md).

## Troubleshooting

- **AppImage segfaults immediately**: the bundled glibc may be too new
  for the host loader. The `AppRun` already routes the main `python` via
  the runtime's `ld-linux`; if the segfault is later, look for a
  sub-process (gst-plugin-scanner, etc.) hitting the same problem.
- **No window appears, no Python traceback**: most likely the host
  `libgdk_pixbuf` overlay was bundled from a too-old build host. Try
  rebuilding from a host with libgdk_pixbuf 2.42+, or override via
  `PITIVI_HOST_PIXBUF=/path/to/libgdk_pixbuf-2.0.so.0`.
- **Pitivi opens but icons are missing**: target host probably lacks
  `librsvg2-common`. Install it, or rely on the PNG fallbacks (which
  cover Pitivi's bundled pixmaps but not arbitrary SVG assets).
- **`Loader process exited early`** in stderr: a glycin loader failed
  inside the sandbox. The libgdk_pixbuf overlay should sidestep this
  for normal image loads; if it persists, a code path is calling
  `libglycin` directly. Check that `bwrap` is installed on the host.
