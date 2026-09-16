#!/usr/bin/env bash
# Source this to get the Pitivi native build environment:
#   source packaging/env.sh
# or:
#   export PITIVI_NATIVE_PREFIX=/path/to/prefix
#   source packaging/env.sh
#
# Install root resolution (first match wins):
#   1. PITIVI_NATIVE_PREFIX   — GStreamer/Pitivi install prefix
#   2. PITIVI_NATIVE_ROOT     — parent dir that contains prefix/
#   3. Sibling of this file:  packaging/../prefix  (repo-local layout)
#   4. Parent of packaging/:  same as (3)
# Intentionally no `set -e` here: this file is sourced into interactive shells.

_PACKAGING_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
_REPO_ROOT="$(cd "$_PACKAGING_DIR/.." && pwd)"

if [ -n "${PITIVI_NATIVE_PREFIX:-}" ]; then
  PREFIX="$PITIVI_NATIVE_PREFIX"
elif [ -n "${PITIVI_NATIVE_ROOT:-}" ]; then
  PREFIX="${PITIVI_NATIVE_ROOT}/prefix"
elif [ -d "$_REPO_ROOT/prefix" ]; then
  PREFIX="$_REPO_ROOT/prefix"
else
  # Documented default for out-of-tree installs next to a checkout
  PREFIX="${PITIVI_NATIVE_PREFIX:-$_REPO_ROOT/prefix}"
fi
export PITIVI_NATIVE_PREFIX="$PREFIX"

# --- Core paths (GStreamer plugins + libs + typelibs) ---
export LD_LIBRARY_PATH="$PREFIX/lib:${LD_LIBRARY_PATH:-}"
export GST_PLUGIN_PATH="$PREFIX/lib/gstreamer-1.0"
export GST_PLUGIN_SYSTEM_PATH="$PREFIX/lib/gstreamer-1.0"
export GI_TYPELIB_PATH="$PREFIX/lib/girepository-1.0:/usr/lib/x86_64-linux-gnu/girepository-1.0:${GI_TYPELIB_PATH:-}"
export PKG_CONFIG_PATH="$PREFIX/lib/pkgconfig:$PREFIX/lib/x86_64-linux-gnu/pkgconfig:${PKG_CONFIG_PATH:-}"

# --- Isolate native GStreamer plugin registry from system GStreamer ---
# Prevents mixing system and prefix plugin caches (stale ranks / missing nvcodec).
export GST_REGISTRY="${GST_REGISTRY:-${XDG_CACHE_HOME:-$HOME/.cache}/pitivi-native-gstreamer-registry}"

# --- Python paths (dual: dist-packages for .py overrides, site-packages for .so) ---
export PYTHONNOUSERSITE=1
export PYTHONPATH="$PREFIX/lib/python3/dist-packages:$PREFIX/lib/python3.12/site-packages:$PREFIX/local/lib/python3.12/dist-packages:${PYTHONPATH:-}"

# --- Binaries (prefix first, then prefix/local for meson etc.) ---
export PATH="$PREFIX/bin:$PREFIX/local/bin:$PATH"

# --- Wayland-only (X11 is unreliable on pure-NVIDIA Pop!_OS / COSMIC) ---
export GDK_BACKEND=wayland

# --- Enable NVIDIA hardware decoders (Pitivi zero-ranks all HW decoders by default) ---
export PITIVI_UNSTABLE_FEATURES=hwdecoders

# --- GStreamer debug (modest; raise to pitivi:4,nvcodec:3 only when debugging) ---
export GST_DEBUG="${GST_DEBUG:-2}"
export GST_DEBUG_NO_COLOR=1

# --- Resource / GPU headroom for single-dGPU systems ---
# Yield GPU to compositor when contested (critical for single-GPU systems)
export __GL_YIELD=1
# Lazy-load CUDA modules -> reduces VRAM footprint
export CUDA_MODULE_LOADING=LAZY
# Limit concurrent CUDA stream connections -> reduces VRAM
export CUDA_DEVICE_MAX_CONNECTIONS=1
# Don't render faster than display needs
export __GL_SYNC_TO_VBLANK=1

# --- VRAM / system-RAM buffer control ---
# Do NOT set GST_DECODER_MAX_FREE_FRAMES or GST_VIDEO_MAX_INPUT_SIZE: those are
# not real GStreamer environment variables. VRAM and system RAM are managed by
# the launcher cgroup caps (MemoryHigh / MemoryMax / MemorySwapMax) plus
# CUDA_MODULE_LOADING=LAZY and CUDA_DEVICE_MAX_CONNECTIONS=1 above.

# --- CUDA NVRTC (runtime kernel compile for nvcodec CUDA converters) ---
# GStreamer hardcodes g_module_open("libnvrtc.so"). Ubuntu/Pop packages only
# ship the SONAME symlink libnvrtc.so.12 (no unversioned .so). Without this,
# cudanvrtc warns and some CUDA colorspace paths may fall back to system memory.
# NVENC/NVDEC themselves do NOT require NVRTC (they use the proprietary driver
# encode/decode engines), but fixing discovery avoids unnecessary CPU converts.
if [ -z "${GST_CUDA_NVRTC_LIBNAME:-}" ]; then
  for _nvrtc in \
    /usr/lib/x86_64-linux-gnu/libnvrtc.so.12 \
    /lib/x86_64-linux-gnu/libnvrtc.so.12 \
    /usr/lib/x86_64-linux-gnu/libnvrtc.so \
    /lib/x86_64-linux-gnu/libnvrtc.so; do
    if [ -e "$_nvrtc" ]; then
      export GST_CUDA_NVRTC_LIBNAME="$_nvrtc"
      break
    fi
  done
  unset _nvrtc
fi
# Also provide unversioned name on LD_LIBRARY_PATH (prefix is already first).
if [ -n "${GST_CUDA_NVRTC_LIBNAME:-}" ] && [ ! -e "$PREFIX/lib/libnvrtc.so" ]; then
  mkdir -p "$PREFIX/lib"
  ln -sfn "$GST_CUDA_NVRTC_LIBNAME" "$PREFIX/lib/libnvrtc.so" 2>/dev/null || true
fi

# --- Proxy speed: skip in-transcode thumbnail/waveform tees (CPU-bound) ---
# When set, proxy.py does not attach teedthumbnailbin/waveformbin. Thumbs and
# waveforms are generated later from the lightweight proxy (or on timeline).
export PITIVI_PROXY_FAST="${PITIVI_PROXY_FAST:-1}"

# --- NVIDIA / CUDA notes (do not invent fake GST_* knobs) ---
# * NVENC/NVDEC ranks are boosted by pitivi/check.py at process start.
# * Do NOT set GST_DECODER_MAX_FREE_FRAMES / GST_VIDEO_MAX_INPUT_SIZE — not real.
# * Optional experiment only (can crash on NVIDIA+Wayland):
#     export PITIVI_UNSTABLE_FEATURES=hwdecoders,gtkglsink
# * Optional debug while validating GPU paths:
#     export GST_DEBUG=2,nvcodec:4,encodebin:3

unset _PACKAGING_DIR _REPO_ROOT
