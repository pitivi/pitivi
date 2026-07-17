# Packaging: native GStreamer nvcodec + Pitivi on single NVIDIA (Wayland)

This directory is **not** intended for GNOME Pitivi upstream as-is. It documents
and ships the out-of-tree launcher used to run a custom prefix where GStreamer
was built with the **nvcodec** plugin (NVDEC/NVENC) against a pure-NVIDIA,
Wayland-only machine (no iGPU).

## Layout

```
packaging/
  env.sh                         # GST/GI/Python/CUDA env (source me)
  pitivi-native.sh               # launcher: source env + cgroup caps + pitivi
  pitivi-native.desktop.example  # desktop entry template
  README.md                      # this file
docs/
  NVIDIA-WAYLAND.md              # full changelog of code + packaging work
```

## Prerequisites

- Proprietary NVIDIA driver with encode/decode support (e.g. GTX 1060+)
- CUDA runtime libraries; NVRTC (`libnvrtc.so.12` on Ubuntu/Pop)
- Wayland session (tested on Pop!_OS COSMIC)
- Custom GStreamer install with `nvcodec` plugin (see build notes below)
- Pitivi built/installed into the same prefix

## Install root (no hardcoded `/mnt` paths)

| Variable | Meaning |
|----------|---------|
| `PITIVI_NATIVE_PREFIX` | Full path to the install prefix (`bin/pitivi`, `lib/gstreamer-1.0`, …) |
| `PITIVI_NATIVE_ROOT` | Parent directory that contains `prefix/` (optional convenience) |

If neither is set, `env.sh` / `pitivi-native.sh` look for `../prefix` relative
to the packaging directory (repo-local layout).

```bash
export PITIVI_NATIVE_PREFIX=/opt/pitivi-native/prefix
source packaging/env.sh
./packaging/pitivi-native.sh
```

## Desktop entry

1. Copy `pitivi-native.desktop.example` to `~/.local/share/applications/pitivi-native.desktop`
2. Set `Exec=` to the **absolute** path of `pitivi-native.sh` (and set
   `PITIVI_NATIVE_PREFIX` in the environment or hardcode it in a wrapper)
3. `update-desktop-database ~/.local/share/applications` if needed

Never point `Exec` at bare `pitivi` without sourcing `env.sh` — you will miss
NVENC rank boosts, NVRTC, isolated registry, and resource caps.

## What env.sh sets

| Area | Variables / behavior |
|------|----------------------|
| Paths | `LD_LIBRARY_PATH`, `GST_PLUGIN_PATH`, `GI_TYPELIB_PATH`, `PKG_CONFIG_PATH`, `PATH`, `PYTHONPATH` |
| Isolation | `PYTHONNOUSERSITE=1`, private `GST_REGISTRY` |
| Display | `GDK_BACKEND=wayland` |
| HW decode | `PITIVI_UNSTABLE_FEATURES=hwdecoders` (NVDEC ranks in `check.py`) |
| CUDA soft caps | `__GL_YIELD=1`, `CUDA_MODULE_LOADING=LAZY`, `CUDA_DEVICE_MAX_CONNECTIONS=1`, `__GL_SYNC_TO_VBLANK=1` |
| NVRTC | Auto-detect `libnvrtc.so.12` → `GST_CUDA_NVRTC_LIBNAME` + unversioned symlink in prefix |
| Proxy speed | `PITIVI_PROXY_FAST=1` (skip in-transcode teedthumbnailbin/waveformbin) |

## What the launcher does

1. Sources `env.sh`
2. Computes 75%/80% of physical RAM for `MemoryHigh` / `MemoryMax`
3. Runs under `systemd-run --user --scope` with:
   - `CPUQuota=70%`
   - `MemoryHigh` / `MemoryMax` / `MemorySwapMax=0`
   - `nice -n 10` / `ionice -c 2 -n 7`
4. Falls back to nice/ionice only if user systemd scopes are unavailable
5. **Never** uses `ulimit -v` (breaks CUDA VA maps; desktop launches reset it)

Rationale: HangWatcher / global OOM history on COSMIC when Pitivi RSS spiked;
cgroup limits confine OOM to the Pitivi scope and leave headroom for the compositor.

## Build GStreamer with nvcodec (outline)

Full sources are **not** committed here. Outline used for this fork:

1. Install NVIDIA driver + CUDA toolkit / NVRTC packages for your distro
2. Build GStreamer **main** (or a release with current nvcodec) into `$PITIVI_NATIVE_PREFIX`
   - Ensure `gst-plugins-bad` / nvcodec is enabled (`-Dnvcodec=enabled` or equivalent)
   - Install into the same prefix as Pitivi
3. Build Pitivi against that prefix (`PKG_CONFIG_PATH`, `meson`, etc.)
4. Verify: `gst-inspect-1.0 nvcodec` and `gst-inspect-1.0 nvautogpuh264enc`

Then launch only via `packaging/pitivi-native.sh`.

## Portable Pitivi code in this fork

See `docs/NVIDIA-WAYLAND.md` for the full inventory. Short list:

- `check.py` — always boost NVENC ranks; NVDEC when `hwdecoders`
- `proxy.py` — transcoder lifecycle, AUTO_NV/ALL_NV, PROXY_FAST, NVENC extension
- `previewers.py` — leaky thumb queue, manager interrupt, proxy-prefer decode
- `render.py` — NVENC first, ETA guards, stall warnings
- project / dialogs / medialibrary / timeline fixes
- NVENC `.gep` / `.prs` presets + tests

## Explicitly not included

- Dual-launcher / mute-all-effects-on-preview hacks
- Claims of full GPU GES/NLE compositing (effects + compositor remain CPU)
- Secrets / tokens
- Full GStreamer source tree

## Upstream note

Official Pitivi lives at [gitlab.gnome.org/GNOME/pitivi](https://gitlab.gnome.org/GNOME/pitivi).
Portable Python/data patches may be proposed upstream as separate MRs.
This `packaging/` tree is machine-specific glue for a native nvcodec prefix.
