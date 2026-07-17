# NVIDIA + Wayland single-dGPU worklog (Xeon E5-2697v2 + GTX 1060)

This document is the accurate inventory of what was done to make Pitivi usable
on a **pure NVIDIA** machine (no iGPU) under **Wayland** (Pop!_OS / COSMIC),
with a **native GStreamer** build that includes **nvcodec** (NVDEC/NVENC).

Hardware reference: **Intel Xeon E5-2697 v2** + **NVIDIA GeForce GTX 1060**.

## Context

- System GStreamer packages do not ship a usable nvcodec path for this setup.
- Pitivi historically zero-ranks hardware decoders and leaves NVENC at rank 0
  (`NONE`), so encodebin ignores it even when the plugin is present.
- Single-GPU Wayland is sensitive to RAM spikes (global OOM freezes the
  compositor) and to GPU contention (need yield + limited CUDA connections).
- Goal: practical acceleration for **proxy encode**, **timeline decode**,
  **thumbnail decode after proxy**, and **render encode** — without pretending
  GES multi-layer compositing or the effect library are GPU.

## Repository layout

```
packaging/
  env.sh
  pitivi-native.sh
  pitivi-native.desktop.example
  README.md
docs/
  NVIDIA-WAYLAND.md          # this file
pitivi/                      # portable application code
data/gstpresets/             # NVENC proxy profiles
tests/                       # coverage for the above
```

Install prefix is **not** hardcoded. Use `PITIVI_NATIVE_PREFIX` (or
`PITIVI_NATIVE_ROOT` with a `prefix/` subdirectory). See `packaging/README.md`.

---

## Infrastructure (`packaging/`)

### Native GStreamer + nvcodec

- Built GStreamer (mainline / 1.29.x era) with nvcodec into a custom prefix.
- Built Pitivi against that prefix (GI typelibs, Python path, plugin path).
- Full GStreamer sources are **not** committed to this fork; only the launch
  glue and Pitivi patches are.

### `env.sh`

| Setting | Why |
|---------|-----|
| `LD_LIBRARY_PATH` / `GST_PLUGIN_PATH` / `GI_TYPELIB_PATH` / `PKG_CONFIG_PATH` / `PATH` / `PYTHONPATH` | Prefer native prefix over system GStreamer |
| `PYTHONNOUSERSITE=1` | Avoid user site-packages shadowing prefix modules |
| Private `GST_REGISTRY` | Do not mix system and prefix plugin caches |
| `GDK_BACKEND=wayland` | X11 was unreliable on this Pop/COSMIC + NVIDIA stack |
| `PITIVI_UNSTABLE_FEATURES=hwdecoders` | Allows `check.py` to boost NVDEC ranks |
| `__GL_YIELD=1` | Yield GPU to compositor under contention |
| `CUDA_MODULE_LOADING=LAZY` | Smaller VRAM footprint at start |
| `CUDA_DEVICE_MAX_CONNECTIONS=1` | Limit concurrent CUDA streams |
| `__GL_SYNC_TO_VBLANK=1` | Do not outrun the display |
| `GST_CUDA_NVRTC_LIBNAME` + unversioned `libnvrtc.so` symlink | GStreamer opens `libnvrtc.so`; distro only ships `libnvrtc.so.12` |
| `PITIVI_PROXY_FAST=1` | Skip CPU-bound teedthumbnailbin/waveformbin during proxy transcode |

**Not set (fake / harmful):** `GST_DECODER_MAX_FREE_FRAMES`, `GST_VIDEO_MAX_INPUT_SIZE`,
`ulimit -v`, GPU TDP power limits.

### `pitivi-native.sh`

1. Resolve install root via env vars (no absolute `/mnt/...` paths in the shipped copy).
2. Source `env.sh`.
3. Launch `$PREFIX/bin/pitivi` under `systemd-run --user --scope` with:
   - `CPUQuota=70%`
   - `MemoryHigh` ≈ 75% of physical RAM
   - `MemoryMax` ≈ 80% of physical RAM
   - `MemorySwapMax=0`
   - `nice -n 10`, `ionice -c 2 -n 7`
4. Fallback: nice/ionice only (still **no** `ulimit -v`).

**Why cgroups:** A HangWatcher / OOM history on COSMIC showed Pitivi reaching
tens of GiB RSS and freezing the whole session. Scope-local MemoryMax confines
failure to Pitivi and leaves compositor headroom. `ulimit -v` is wrong for CUDA
(virtual address space) and is reset by desktop launches.

### Desktop entry

Example: `packaging/pitivi-native.desktop.example`.
`Exec` must point at the launcher (which sources env), never bare `pitivi`.

---

## Pitivi code (portable)

### `pitivi/utils/proxy.py`

- Tear down GstTranscoder jobs on **error** and **cancel** (disconnect signals,
  stop transcoder, drop `.part` files, advance queue). Failed jobs no longer
  stick in the running list and block new work.
- Progress ETA guards against **divide-by-zero** when position is still 0.
- Fix **video/x-raw** caps typo.
- Proxy strategies: **`AUTO_NV`** (default) and **`ALL_NV`**.
- Prefer **NVENC** encoding profile when available (`.proxy.nv.mkv` extension).
- Default **`num_transcoding_jobs=1`** for single-dGPU systems.
- **`PITIVI_PROXY_FAST`**: skip attaching teedthumbnailbin/waveformbin during
  transcode (those paths force every frame through CPU convert and OOM easily).
- **`get_preview_source_asset()`**: prefer ready proxy for preview/thumbnail
  decode; identity/cache still keys by original.

### `pitivi/timeline/previewers.py`

- TeedThumbnailBin queue: **`max-size-buffers=1`**, **`leaky=downstream`**
  (was unlimited → tens of GB RSS under fast decode).
- **PreviewerManager**: pause / interrupt / resume; interrupt does not start
  new jobs mid-stop; resume drains queue if current previewer was destroyed.
- **ThumbnailCache.close_all** on project release; pixbuf **LRU** cap.
- Temporary **NVDEC** rank boost for thumb pipelines only (push/pop).
- Prefer **proxy** media for thumbs/waveforms when ready
  (`get_preview_source_asset`).

### `pitivi/check.py`

- **Always** boost NVENC factory ranks to **258** when factories exist
  (`nvautogpuh264enc`, `nvautogpuh265enc`, `nvh264enc`, `nvh265enc`, …).
  nvcodec ships many encoders at rank 0; without this, encodebin picks CPU.
- Boost **NVDEC** ranks to 258 only when `hwdecoders` is in
  `PITIVI_UNSTABLE_FEATURES`.

### `pitivi/render.py`

- **NVENC first** in supported encoder combinations (`nvautogpuh264enc` /
  `nvautogpuh265enc` — system-memory-friendly autogpu variants).
- **QualityAdapter** bitrate tables for NVENC H.264/H.265.
- **`compute_render_eta`**: minimum media/wall progress, EMA smoothing, cap;
  avoids multi-day ETAs from near-zero position.
- **Stall warning** if position does not advance.
- Encoder/muxer logging at render start.

### `pitivi/project.py` / dialogs / medialibrary / timeline

- **Dirty flag** restored after export (export used save path that cleared dirty).
- **Relocation** can mark dirty during load.
- **Autosave** under sustained edits (polling could never hit threshold while
  continuously dirty-editing).
- **ThumbnailCache.close_all** on project release.
- **medialibrary**: COMBO_STRATEGIES Smart → AUTO_NV mapping; None extension
  guard; menu/progress hardening.
- **missingasset** dialog: Cancel returns correctly (no highlighted-URI trap).
- **prefs**: fix accel-changed handler leaks.
- **timeline elements**: keyframe signal disconnect; duplicate only-once effect
  returns None instead of reordering wrongly.
- **timeline.py**: rebind previewers after proxy asset switch.

### Presets (`data/gstpresets/`)

- `nvenc-h264-raw-in-mkv.gep` / `nvenc-h264-raw-in-mp4.gep`
- `GstNvAutoGpuH264Enc.prs` (Proxy Fast / Proxy Quality bitrate presets)

### Tests

- `tests/test_proxy.py` — cancel/error lifecycle, related proxy behavior
- `tests/test_previewers.py` — queue bounds, manager, cache close
- `tests/test_project.py` — dirty/export/autosave
- `tests/test_render.py` — ETA helpers
- `tests/test_timeline_elements.py` — keyframe / effect edge cases

---

## What uses NVIDIA vs what stays CPU

| Path | NVIDIA? | Mechanism |
|------|---------|-----------|
| Startup ranks | yes | `check.py` NVENC always; NVDEC with hwdecoders |
| Proxy encode | yes | NVENC gep + rank boost |
| Proxy decode (input) | yes | uridecodebin autoplug → NVDEC |
| Render encode | yes | NVENC first + QualityAdapters |
| Timeline play (sources) | partial | NVDEC on sources; GES compositor CPU |
| Thumbs after proxy | yes (improved) | Prefer proxy + temporary NVDEC boost |
| Effects / transitions | **no** | CPU (no CUDA effect library) |
| GES multi-layer composite | **no** | No CUDA compositor in this stack |
| Video sink | **no** | `gtksink` (gtkglsink unstable on NVIDIA+Wayland) |
| Audio / waveforms peaks | **no** | CPU |

---

## Explicitly NOT included

- Dual launcher / mute-all-effects-on-preview nonsense
- Flowerly claims of “full GPU NLE”
- GPU effect library / CUDA compositor integration
- Secrets, PATs, tokens
- Hardcoded absolute `/mnt/...` install paths in shipped packaging
- Full GStreamer source tree

---

## How to run

```bash
export PITIVI_NATIVE_PREFIX=/path/to/your/prefix
# optional: export PITIVI_PROXY_FAST=1   # default in env.sh
./packaging/pitivi-native.sh
```

Verify ranks in the terminal at startup (NVENC → 258; NVDEC when hwdecoders).
During proxy/render, `nvidia-smi dmon -s u` should show **enc** / **dec** activity.

---

## Branch / contribution map (GitHub fork)

Small portable PRs (code only):

1. `fix/proxy-transcoder-lifecycle` — proxy cancel/error/ETA/caps
2. `fix/previewers-thumbnail-queue` — thumb queue OOM + close_all
3. `fix/project-dialogs-timeline` — dirty/autosave/UI/timeline rebind
4. `fix/render-eta-and-nvenc-list` — render ETA + NVENC list
5. `feature/nvenc-check-ranks` — check.py ranks
6. `feature/proxy-nvenc-presets` — .gep/.prs

Combined branch (code + packaging + this doc):

- `feature/nvidia-wayland-single-dgpu-full`

Supersedes the older informal branch
`feature/nvidia-sorta-works-xeon-e5-2697v2-gtx1060` (deleted; PR closed).

---

## License / upstream

Pitivi code remains under the project’s existing license terms.
Propose portable patches to [GNOME Pitivi](https://gitlab.gnome.org/GNOME/pitivi)
via GitLab MRs as appropriate; keep packaging machine-local unless upstream
wants optional native-prefix docs.
