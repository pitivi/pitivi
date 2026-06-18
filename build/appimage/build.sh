#!/bin/bash
# Build a standalone Pitivi AppImage from the published Flathub deployment.
#
# Strategy: install (or use) `org.pitivi.Pitivi` from Flathub --user, then
# hardlink its /app + bundled GNOME runtime tree into an AppDir, layer in a
# host libgdk_pixbuf to sidestep glycin, render PNG fallbacks for SVG icons,
# and pack everything with appimagetool. The actual fixups are done at run
# time by AppRun + launcher.py — files in the flatpak deployment are NEVER
# modified in place.
#
# Usage:
#   ./build.sh [--out DIR] [--keep-appdir] [--no-flatpak-install]
#
# Run with --help for the full option list.

set -euo pipefail

usage() {
    cat <<EOF
Usage: $0 [options]

Options:
  --out DIR              Write the AppImage to DIR (default: current dir).
  --keep-appdir          Don't delete _build/AppDir after packing.
  --no-flatpak-install   Skip 'flatpak install', use what's already there.
  --comp <zstd|gzip|xz|none>
                         squashfs compression (default: zstd).
                         zstd = current default; only one supported by
                                the bundled mksquashfs in modern
                                appimagetool. Excellent ratio + fast
                                decompress.
                         gzip = legacy. May or may not be supported
                                depending on appimagetool version.
                         xz   = legacy. Same caveat as gzip.
                         none = no compression (debug).
  --lean                 Drop bundle bits Pitivi doesn't strictly need:
                         WebKit + JS engines (~270 MB, breaks the in-app
                         help viewer; online help still works), mythes,
                         docs/man/headers/static libs (~30 MB), and the
                         shipped __pycache__ (~130 MB; Python regenerates
                         pyc on first use, slightly slower first launch).
  -h, --help             Show this help.

Environment overrides:
  PITIVI_REF             flatpak ref to bundle (default: org.pitivi.Pitivi//stable).
  PITIVI_HOST_PIXBUF     full path to a host libgdk_pixbuf-2.0.so.0 to use as
                         overlay (default: auto-detected via uname -m).
EOF
}

# ---------- args -----------
OUT_DIR="."
KEEP_APPDIR=0
DO_INSTALL=1
COMP="zstd"
LEAN=0
PITIVI_REF="${PITIVI_REF:-org.pitivi.Pitivi//stable}"
while [ $# -gt 0 ]; do
    case "$1" in
        --out)                 OUT_DIR="$2"; shift 2 ;;
        --keep-appdir)         KEEP_APPDIR=1; shift ;;
        --no-flatpak-install)  DO_INSTALL=0; shift ;;
        --comp)                COMP="$2"; shift 2 ;;
        --lean)                LEAN=1; shift ;;
        -h|--help)             usage; exit 0 ;;
        *) echo "unknown arg: $1" >&2; usage >&2; exit 64 ;;
    esac
done

case "$COMP" in
    gzip|xz|zstd|none) ;;
    *) echo "invalid --comp: $COMP (use gzip|xz|zstd|none)" >&2; exit 64 ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORK_DIR="$SCRIPT_DIR/_build"
APPDIR="$WORK_DIR/AppDir"

# ---------- 0. environment audit ----------
echo "[0/6] auditing build host..."

# Architecture is the only thing we need before anything else, because the
# rest of the script branches on it.
ARCH="$(uname -m)"
case "$ARCH" in
    x86_64)  ARCH_TRIPLE=x86_64-linux-gnu ;;
    aarch64) ARCH_TRIPLE=aarch64-linux-gnu ;;
    *) echo "unsupported architecture: $ARCH" >&2; exit 1 ;;
esac
echo "    arch         : $ARCH ($ARCH_TRIPLE)"

# Required tools. We treat each one as a separate, named requirement so the
# error message tells the user exactly what to install.
need() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "missing tool '$1' — $2" >&2
        exit 1
    fi
    echo "    $1$(printf '%*s' $((12 - ${#1})) '') : $(command -v "$1")"
}
need flatpak  "install flatpak (1.12+); needed to fetch the Pitivi deployment"
need convert  "install ImageMagick; needed to render PNG fallbacks for SVG icons"
need wget     "install wget; needed once to fetch appimagetool"
need find     "install findutils"
need sed      "install sed"
need install  "install coreutils"
need objdump  "install binutils; needed to walk host-libs deps"

# Optional tools — warn but don't abort.
opt() {
    if command -v "$1" >/dev/null 2>&1; then
        echo "    $1$(printf '%*s' $((12 - ${#1})) '') : $(command -v "$1") (optional)"
    else
        echo "    $1$(printf '%*s' $((12 - ${#1})) '') : NOT FOUND ($2)" >&2
    fi
}
opt bwrap  "host bubblewrap; the AppImage's glycin sandbox needs it on the *target* host"

# SVG renderer for the PNG fallbacks: prefer rsvg-convert (no policy
# minefield), fall back to ImageMagick `convert` when missing. We check
# both up front so we know which one to use later (step 5).
SVG_RENDERER=""
if command -v rsvg-convert >/dev/null 2>&1; then
    SVG_RENDERER=rsvg-convert
    echo "    rsvg-convert : $(command -v rsvg-convert)"
elif convert -list format 2>/dev/null \
     | awk '/^[ \t]+M?SVG[ \t]/{found=1} END{exit !found}'; then
    SVG_RENDERER=convert
    echo "    SVG renderer : ImageMagick convert"
else
    echo "    WARNING: no SVG renderer (rsvg-convert / convert with SVG" >&2
    echo "    support) found; PNG fallbacks for Pitivi pixmaps won't be" >&2
    echo "    generated. The AppImage will rely on the target host's" >&2
    echo "    librsvg2-common. Install librsvg2-bin to fix." >&2
fi

# Make sure WORK_DIR exists before we use it (the disk-space check below
# needs it). On a fresh checkout it doesn't.
mkdir -p "$WORK_DIR"

# Disk space — the AppDir is ~1.6 GB hardlinks (cheap), but mksquashfs
# reads the whole thing and writes a ~600 MB AppImage; needing 2 GB free
# at minimum is reasonable. Wrap in `|| true` so a transient `df` failure
# doesn't kill the build under `set -e + pipefail`.
FREE_KB="$(df -kP "$WORK_DIR" 2>/dev/null | awk 'NR==2{print $4}' || true)"
if [ -n "${FREE_KB:-}" ] && [ "$FREE_KB" -lt $((2 * 1024 * 1024)) ]; then
    echo "    WARNING: less than 2 GB free at $WORK_DIR; build may fail." >&2
fi

# ---------- 1. flatpak install/refresh ----------
if [ "$DO_INSTALL" = 1 ]; then
    if ! flatpak remote-list --user | grep -q '^flathub'; then
        echo "[1/6] adding flathub remote (--user)..."
        flatpak remote-add --user --if-not-exists flathub \
            https://flathub.org/repo/flathub.flatpakrepo
    fi
    echo "[1/6] installing/updating $PITIVI_REF from flathub..."
    flatpak install --user --noninteractive --or-update flathub "$PITIVI_REF" >/dev/null
else
    echo "[1/6] skipping flatpak install (--no-flatpak-install)"
fi

# ---------- 2. resolve deployment paths ----------
echo "[2/6] resolving deployment paths..."
PITIVI_ID="${PITIVI_REF%%//*}"
PITIVI_DEP="$(flatpak info --user --show-location "$PITIVI_ID")/files"
[ -d "$PITIVI_DEP" ] || { echo "Pitivi flatpak '$PITIVI_ID' not installed"; exit 1; }

# The Pitivi flatpak metadata names which runtime + extensions it pulled in.
RUNTIME_REF="$(grep -m1 '^runtime=' "$(dirname "$PITIVI_DEP")/metadata" | cut -d= -f2)"
[ -n "$RUNTIME_REF" ] || { echo "could not parse runtime= from metadata"; exit 1; }
RUNTIME_DEP="$(flatpak info --user --show-location "${RUNTIME_REF#runtime/}")/files"
[ -d "$RUNTIME_DEP" ] || { echo "runtime $RUNTIME_REF not installed"; exit 1; }

# Codecs extension is optional but recommended for full format coverage.
CODECS_REF="${PITIVI_ID}.Codecs"
CODECS_DEP=""
if flatpak info --user "$CODECS_REF" >/dev/null 2>&1; then
    CODECS_DEP="$(flatpak info --user --show-location "$CODECS_REF")/files"
fi

PITIVI_VER="$(flatpak info --user "$PITIVI_ID" | awk '/Version:/ {print $2}')"
echo "    pitivi  : $PITIVI_DEP  (v$PITIVI_VER)"
echo "    runtime : $RUNTIME_DEP  ($RUNTIME_REF)"
echo "    codecs  : ${CODECS_DEP:-<none>}"

# Sanity-check the runtime ships a python (the AppRun depends on it).
if ! ls "$RUNTIME_DEP"/bin/python3.* >/dev/null 2>&1; then
    echo "    ERROR: runtime ships no python3.*; nothing for AppRun to exec." >&2
    exit 1
fi

# ---------- 3. compose AppDir ----------
echo "[3/6] composing AppDir (hardlinks)..."
rm -rf "$APPDIR"
mkdir -p "$APPDIR"
cp -al "$RUNTIME_DEP" "$APPDIR/runtime"
cp -al "$PITIVI_DEP"  "$APPDIR/app"
[ -n "$CODECS_DEP" ] && cp -al "$CODECS_DEP" "$APPDIR/codecs" || mkdir "$APPDIR/codecs"

# Drop in our hand-written entry points + wrappers (overwriting any prior
# stale copies).
install -m 0755 "$SCRIPT_DIR/AppRun"      "$APPDIR/AppRun"
install -m 0644 "$SCRIPT_DIR/launcher.py" "$APPDIR/launcher.py"
install -d                                  "$APPDIR/wrappers"
install -m 0755 "$SCRIPT_DIR/wrappers/bwrap" "$APPDIR/wrappers/bwrap"

# Drop GIO modules that have unresolvable dependencies in our bundle.
# The GNOME runtime ships gvfs-* modules that reference libgvfscommon.so
# (and similar gvfs internals) which aren't bundled — at every load
# attempt the user gets "Failed to load module: libgvfscommon.so: cannot
# open shared object file". Pitivi doesn't need gvfs (remote filesystems
# like smb://, sftp://) so we remove every broken module here.
#
# `rm` on a hardlink only unlinks our copy; the user's flatpak install
# stays intact.
GIO_MODULES_DIR="$APPDIR/runtime/lib/$ARCH_TRIPLE/gio/modules"
if [ -d "$GIO_MODULES_DIR" ]; then
    removed=0
    for mod in "$GIO_MODULES_DIR"/*.so; do
        [ -f "$mod" ] || continue
        broken_dep=""
        for dep in $(objdump -p "$mod" 2>/dev/null \
                     | awk '/NEEDED/ {print $2}'); do
            # Already shipped by the bundled runtime?
            for d in "$APPDIR/runtime/lib/$ARCH_TRIPLE" \
                     "$APPDIR/runtime/lib" "$APPDIR/runtime/lib64" \
                     "$APPDIR/host-libs"; do
                [ -e "$d/$dep" ] && continue 2
            done
            # Glibc family — provided by every host loader.
            case "$dep" in
                libc.so.*|libm.so.*|libdl.so.*|libpthread.so.*|\
                librt.so.*|libresolv.so.*|libgcc_s.so.*|ld-linux*) \
                    continue ;;
            esac
            broken_dep="$dep"
            break
        done
        if [ -n "$broken_dep" ]; then
            echo "    drop GIO module $(basename "$mod")  (needs $broken_dep)"
            rm -f "$mod"
            removed=$((removed+1))
        fi
    done
    if [ "$removed" -gt 0 ]; then
        echo "    dropped $removed broken GIO module(s)"
        # giomodule.cache references the deleted modules; drop it so GIO
        # regenerates the cache from the surviving .so files at startup.
        rm -f "$GIO_MODULES_DIR/giomodule.cache"
    fi
fi

# Required by appimagetool: top-level .desktop + matching icon.
cp "$APPDIR/app/share/applications/${PITIVI_ID}.desktop" "$APPDIR/"
cp "$APPDIR/app/share/icons/hicolor/scalable/apps/${PITIVI_ID}.svg" "$APPDIR/"
ln -sf "${PITIVI_ID}.svg" "$APPDIR/.DirIcon"
sed -i 's|^Exec=.*|Exec=AppRun %U|; s|^TryExec=.*|TryExec=AppRun|' \
    "$APPDIR/${PITIVI_ID}.desktop"

# ---------- 4. host libgdk_pixbuf overlay ----------
# Replace the runtime's libgdk_pixbuf (linked to libglycin, which sandboxes
# loaders via bwrap and can't reach its bundled binaries on a non-GNOME
# host) with the host distro's copy. We MUST NOT touch the runtime tree
# itself (hardlinked into the user's flatpak install); instead we ship the
# replacement under host-libs/ and put it first on LD_LIBRARY_PATH.
echo "[4/6] staging host libgdk_pixbuf overlay..."
mkdir -p "$APPDIR/host-libs"
HOST_PIXBUF="${PITIVI_HOST_PIXBUF:-/usr/lib/$ARCH_TRIPLE/libgdk_pixbuf-2.0.so.0}"
if [ -f "$HOST_PIXBUF" ]; then
    cp -L "$HOST_PIXBUF" "$APPDIR/host-libs/libgdk_pixbuf-2.0.so.0"
    # `strings` returns several version-shaped tokens (the ABI marker
    # 2.10.0 and the real release 2.4X.Y). Pick the highest 2.4X.Y match.
    PIXBUF_VER="$(strings "$APPDIR/host-libs/libgdk_pixbuf-2.0.so.0" \
                  | grep -E '^2\.4[0-9]+\.[0-9]+$' | sort -V | tail -1)"
    : "${PIXBUF_VER:=unknown}"
    echo "    using $HOST_PIXBUF (v$PIXBUF_VER)"
    if [ "$PIXBUF_VER" != unknown ]; then
        minor="${PIXBUF_VER#2.}"; minor="${minor%%.*}"
        if [ "${minor:-0}" -lt 42 ]; then
            echo "    WARNING: host libgdk_pixbuf is older than 2.42; may be" >&2
            echo "    ABI-incompatible with the bundled GTK." >&2
        fi
    fi

    # Recursively bundle every NEEDED dep of the overlaid lib that is
    # absent from the runtime. The build host's libgdk_pixbuf may pull in
    # libs (e.g. libjpeg.so.8) that aren't shipped in the GNOME runtime
    # nor present on the target host's distribution, which would break
    # typelib resolution at run time.
    #
    # NEVER bundle the glibc core: bundling libc/libm/libpthread/ld-linux
    # would require the *target* host's loader to load a possibly newer
    # libc, which segfaults. The bundled runtime already ships its own
    # full glibc set under runtime/lib/.
    is_core() {
        case "$1" in
            libc.so.*|libm.so.*|libdl.so.*|libpthread.so.*|librt.so.*|\
            libresolv.so.*|libnss_*|libutil.so.*|libcrypt.so.*|\
            libanl.so.*|libBrokenLocale.so.*|libthread_db.so.*|\
            ld-linux*|ld-musl-*|libgcc_s.so.*) return 0 ;;
            *) return 1 ;;
        esac
    }
    in_runtime() {
        for d in "$APPDIR/runtime/lib/$ARCH_TRIPLE" \
                 "$APPDIR/runtime/lib" "$APPDIR/runtime/lib64"; do
            [ -e "$d/$1" ] && return 0
        done
        return 1
    }
    bundled_count=0; missing_count=0
    queue=("libgdk_pixbuf-2.0.so.0")
    declare -A seen=()
    while [ ${#queue[@]} -gt 0 ]; do
        lib="${queue[0]}"; queue=("${queue[@]:1}")
        [ -n "${seen[$lib]:-}" ] && continue
        seen[$lib]=1
        [ -f "$APPDIR/host-libs/$lib" ] || continue
        # objdump avoids the env-pollution risks of ldd
        for dep in $(objdump -p "$APPDIR/host-libs/$lib" 2>/dev/null \
                     | awk '/NEEDED/ {print $2}'); do
            is_core "$dep" && continue
            in_runtime "$dep" && continue
            [ -f "$APPDIR/host-libs/$dep" ] && { queue+=("$dep"); continue; }
            # find on host
            host_path=""
            for dir in "/usr/lib/$ARCH_TRIPLE" /usr/lib \
                       "/lib/$ARCH_TRIPLE" /lib; do
                if [ -f "$dir/$dep" ]; then
                    host_path="$dir/$dep"; break
                fi
            done
            if [ -n "$host_path" ]; then
                cp -L "$host_path" "$APPDIR/host-libs/$dep"
                echo "    bundled $dep  (from $host_path)"
                bundled_count=$((bundled_count+1))
                queue+=("$dep")
            else
                echo "    WARNING: dep '$dep' (needed by $lib) not found on host" >&2
                missing_count=$((missing_count+1))
            fi
        done
    done
    if [ "$bundled_count" = 0 ] && [ "$missing_count" = 0 ]; then
        echo "    no extra deps needed (runtime covers everything)"
    else
        echo "    bundled $bundled_count extra dep(s), $missing_count missing"
    fi
else
    echo "    WARNING: $HOST_PIXBUF not found on build host; the AppImage" >&2
    echo "    will fall back to the runtime's glycin-based loader and may" >&2
    echo "    fail to load images on a host without GNOME libs." >&2
fi

# ---------- 5. render PNG fallbacks for Pitivi SVGs ----------
# The runtime libgdk_pixbuf comes from a different distro than the target's
# librsvg2-common; if SVG loading fails at run time, launcher.py falls back
# to a sibling .png that we render here once at build time.
echo "[5/6] rendering PNG fallbacks for SVG pixmaps..."
made=0; failed=0
render_svg_to_png() {
    case "$SVG_RENDERER" in
        rsvg-convert) rsvg-convert -w "$3" -h "$3" "$1" -o "$2" 2>/dev/null ;;
        convert)      convert -background none -resize "${3}x${3}" "$1" "$2" 2>/dev/null ;;
        *)            return 1 ;;
    esac
}
# We render PNG siblings for two SVG locations:
#   1. app/share/pitivi/pixmaps/  — Pitivi's bundled UI icons.
#   2. app/share/icons/hicolor/scalable/apps/  — the app icon, which
#      Pitivi loads via Gtk.IconTheme.load_icon. On hosts whose gdk-pixbuf
#      can't find an SVG loader (Fedora/Arch path layout differs from
#      Debian/Ubuntu, so our bundled loaders.cache misses), the launcher
#      falls back to the PNG sibling.
if [ -n "$SVG_RENDERER" ]; then
    for src_pair in \
        "$APPDIR/app/share/pitivi/pixmaps:128" \
        "$APPDIR/app/share/icons/hicolor/scalable/apps:256"; do
        dir="${src_pair%:*}"
        size="${src_pair##*:}"
        [ -d "$dir" ] || continue
        while IFS= read -r svg; do
            png="${svg%.svg}.png"
            if [ ! -e "$png" ]; then
                if render_svg_to_png "$svg" "$png" "$size"; then
                    made=$((made+1))
                else
                    failed=$((failed+1))
                fi
            fi
        done < <(find "$dir" -name '*.svg')
    done
    echo "    rendered $made new PNGs, $failed failed (via $SVG_RENDERER)"
else
    echo "    skipped: no SVG renderer available"
fi

# ---------- 5b. trim (--lean only) ----------
# Removing files inside the AppDir is safe: hardlinks share inodes but
# `rm` only unlinks the AppDir's directory entry; the user's flatpak
# deployment keeps its own hardlinks and stays intact.
if [ "$LEAN" = 1 ]; then
    echo "[5b/6] --lean: trimming non-essential files..."
    before=$(du -sb "$APPDIR" | awk '{print $1}')

    # WebKit + its JS engines + the in-app help viewer (libyelp). Pitivi
    # never imports WebKit; only `libyelp` does, and we lose only the
    # offline help viewer (online help via pitivi.org still works).
    rm -f \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/libwebkit*.so* \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/libwebkitgtk*.so* \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/libjavascriptcoregtk*.so* \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/libmozjs*.so* \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/libyelp*.so* \
        "$APPDIR/runtime/lib/$ARCH_TRIPLE"/girepository-1.0/{WebKit,JavaScriptCore,Yelp}*.typelib \
        2>/dev/null || true

    # Static libs and headers — never useful at runtime.
    find "$APPDIR" -name '*.a' -delete 2>/dev/null
    rm -rf "$APPDIR/runtime/include" "$APPDIR/app/include"

    # Doc trees.
    rm -rf \
        "$APPDIR/runtime/share/doc" "$APPDIR/app/share/doc" \
        "$APPDIR/runtime/share/man" "$APPDIR/app/share/man" \
        "$APPDIR/runtime/share/gtk-doc" \
        "$APPDIR/runtime/share/devhelp" \
        "$APPDIR/runtime/share/info"

    # Mythes (LibreOffice thesaurus) — Pitivi never uses it.
    rm -rf "$APPDIR/runtime/share/mythes"

    # Bytecode caches — Python recreates on first use; first launch is
    # slightly slower but the AppImage shrinks by ~130 MB.
    find "$APPDIR" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null

    after=$(du -sb "$APPDIR" | awk '{print $1}')
    saved=$(( (before - after) / 1024 / 1024 ))
    echo "    AppDir went from $((before/1024/1024)) MB to $((after/1024/1024)) MB (saved $saved MB)"
fi

# ---------- 6. pack ----------
echo "[6/6] packing AppImage..."
APPIMAGETOOL_DL="$WORK_DIR/appimagetool"
if [ ! -x "$APPIMAGETOOL_DL" ]; then
    # Use the active AppImage/appimagetool repo (NOT the deprecated
    # AppImageKit). The old AppImageKit continuous build had a bug in
    # arch detection that mistakenly treated `file`(1) outputs "aarch64"
    # and "ARM aarch64" as separate architectures, causing aarch64
    # builds to fail with a bogus "More than one architectures" message
    # even when ARCH was exported. The new repo also ships a single
    # static-pie ELF instead of a nested AppImage, so we can invoke it
    # directly.
    case "$ARCH" in
        x86_64)  AT_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" ;;
        aarch64) AT_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-aarch64.AppImage" ;;
    esac
    echo "    fetching appimagetool from $AT_URL"
    wget -q "$AT_URL" -O "$APPIMAGETOOL_DL"
    chmod +x "$APPIMAGETOOL_DL"
fi
APPIMAGETOOL_BIN="$APPIMAGETOOL_DL"

OUT_NAME="Pitivi-${PITIVI_VER:-snapshot}-${ARCH}.AppImage"
mkdir -p "$OUT_DIR"
# Pass --comp through to mksquashfs. Default zstd is the only compressor
# the modern AppImage/appimagetool's bundled mksquashfs supports; gzip/xz
# require an external mksquashfs build, which is fragile across distros.
APPIMAGE_COMP_ARGS=()
[ "$COMP" = none ] || APPIMAGE_COMP_ARGS=(--comp "$COMP")
# Always export ARCH so the appimagetool sub-process picks the right
# embedded runtime (its own arch sniffing fails on AppDirs that mix
# native binaries with sandbox bits like glycin loaders).
export ARCH
"$APPIMAGETOOL_BIN" --no-appstream \
    "${APPIMAGE_COMP_ARGS[@]}" "$APPDIR" "$OUT_DIR/$OUT_NAME"

if [ "$KEEP_APPDIR" = 0 ]; then
    rm -rf "$APPDIR"
fi

echo
echo "Done: $OUT_DIR/$OUT_NAME"
ls -lh "$OUT_DIR/$OUT_NAME"
