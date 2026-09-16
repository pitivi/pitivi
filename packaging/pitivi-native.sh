#!/usr/bin/env bash
# Pitivi native build launcher — pure-NVIDIA, Wayland-only, NVDEC/NVENC enabled
#
# Typical use:
#   export PITIVI_NATIVE_PREFIX=/path/to/prefix
#   ./packaging/pitivi-native.sh
#
# Or with install root that contains prefix/ and this packaging/ tree:
#   export PITIVI_NATIVE_ROOT=/path/to/pitivi-native
#   $PITIVI_NATIVE_ROOT/packaging/pitivi-native.sh
#
# Resource caps (NO GPU TDP/power limit — intentionally not used):
#   CPU  : 70%  — systemd-run --user --scope --property=CPUQuota=70% (+ nice/ionice)
#   RAM  : 80%  — MemoryMax = 80% of physical RAM
#                 MemoryHigh soft limit (~75%) + MemorySwapMax=0 (no swap thrashing)
#                 (cgroup v2, kernel-enforced, cgroup-local OOM — leaves >=20% for compositor)
#   GPU  : soft  — single CUDA context, yield-to-compositor, vblank sync, 1 proxy job
#   VRAM : soft  — lazy CUDA module loading
#
# WHY cgroup MemoryMax (not ulimit -v):
#   - Desktop Exec launches reset shell ulimits; ulimit -v is not reliable for .desktop.
#   - ulimit -v caps *virtual address space*, which breaks CUDA/NVDEC large VA mappings.
#   - A prior crash showed python3 at ~62 GiB vm / ~23 GiB anon-rss, triggering a *global*
#     OOM that froze COSMIC. MemoryMax on a scope confines the spike to Pitivi only.
#   - Fallback path intentionally does NOT use ulimit -v.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Prefer explicit install root; otherwise assume packaging/ lives next to prefix/
if [ -n "${PITIVI_NATIVE_ROOT:-}" ]; then
  NATIVE_ROOT="$PITIVI_NATIVE_ROOT"
elif [ -d "$REPO_ROOT/prefix" ]; then
  NATIVE_ROOT="$REPO_ROOT"
else
  NATIVE_ROOT="$REPO_ROOT"
fi

if [ -z "${PITIVI_NATIVE_PREFIX:-}" ]; then
  export PITIVI_NATIVE_PREFIX="${NATIVE_ROOT}/prefix"
fi
PREFIX="$PITIVI_NATIVE_PREFIX"

# ======================================================================
# Environment (GStreamer paths + resource/GPU/VRAM env vars)
# ======================================================================
# shellcheck source=env.sh
source "$SCRIPT_DIR/env.sh"

if [ ! -x "$PREFIX/bin/pitivi" ]; then
  echo "[pitivi-native] ERROR: $PREFIX/bin/pitivi not found or not executable." >&2
  echo "[pitivi-native] Set PITIVI_NATIVE_PREFIX to your install prefix and rebuild." >&2
  exit 1
fi

# ======================================================================
# RAM budget: 80% of physical RAM (bytes), computed at runtime
# ======================================================================
RAM_TOTAL_BYTES=$(free -b | awk '/^Mem:/ {print $2}')
RAM_80PCT_BYTES=$(( RAM_TOTAL_BYTES * 80 / 100 ))
# Soft limit ~75%: reclaim pressure before hard OOM at MemoryMax
RAM_75PCT_BYTES=$(( RAM_TOTAL_BYTES * 75 / 100 ))
RAM_80PCT_MB=$(( RAM_80PCT_BYTES / 1024 / 1024 ))
RAM_75PCT_MB=$(( RAM_75PCT_BYTES / 1024 / 1024 ))

echo "[pitivi-native] PREFIX=$PREFIX"
echo "[pitivi-native] RAM total: $(( RAM_TOTAL_BYTES / 1024 / 1024 ))MB  ->  MemoryHigh: ${RAM_75PCT_MB}MB  MemoryMax: ${RAM_80PCT_MB}MB"
echo "[pitivi-native] CPU cap: 70% (CPUQuota)   | scheduler: nice=10   | I/O: best-effort prio 7"
echo "[pitivi-native] GPU cap: no TDP limit; using CUDA_DEVICE_MAX_CONNECTIONS=1, __GL_YIELD=1, 1 proxy job"

# ======================================================================
# Launch Pitivi with cgroup resource caps (primary path)
# ======================================================================
# systemd-run --user --scope registers this process subtree in a transient
# user scope with MemoryHigh + MemoryMax + MemorySwapMax + CPUQuota applied
# at the cgroup level. Probe by actually trying systemd-run (not
# is-system-running, which returns non-zero for "degraded").

CAN_SYSTEMD=0
if command -v systemd-run >/dev/null 2>&1 && \
   systemd-run --user --scope true >/dev/null 2>&1; then
    CAN_SYSTEMD=1
fi

if [ "$CAN_SYSTEMD" -eq 1 ]; then
    echo "[pitivi-native] Launching under systemd --user --scope (MemoryHigh=${RAM_75PCT_MB}M, MemoryMax=${RAM_80PCT_MB}M, MemorySwapMax=0, CPUQuota=70%)..."
    exec systemd-run --user --scope \
        --property=CPUQuota=70% \
        --property=MemoryHigh=${RAM_75PCT_BYTES} \
        --property=MemoryMax=${RAM_80PCT_BYTES} \
        --property=MemorySwapMax=0 \
        nice -n 10 ionice -c 2 -n 7 \
        "$PREFIX/bin/pitivi" "$@"
fi

# --- Fallback (user manager / systemd-run not usable) ---
# No ulimit -v: virtual address space caps break CUDA/NVDEC.
# Without cgroup MemoryMax we cannot enforce a hard RAM cap; rely on nice/ionice only.
echo "[pitivi-native] WARNING: systemd --user scope unavailable; falling back to nice/ionice only (no RAM cgroup cap)."
exec nice -n 10 ionice -c 2 -n 7 \
    "$PREFIX/bin/pitivi" "$@"
