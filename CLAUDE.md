# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development environment

All build/test/run commands must execute inside the project's Flatpak sandbox. The sandbox is entered by sourcing the env script, which sets up aliases that wrap commands with `ptvenv` (the sandbox runner at `build/flatpak/pitivi-flatpak`):

```
$ . bin/pitivi-env        # sets up the (ptv-flatpak) prompt and aliases
```

Initial sandbox creation can take hours. After a fresh sandbox is built, the script tells you to **close and reopen the terminal** so the aliases are picked up. Update the sandbox with `ptvenv --update`.

If you cannot enter the sandbox, prefix any command with `ptvenv` directly (e.g. `ptvenv ninja -C mesonbuild/`). Running Python tools on the host will fail because GStreamer/GES typelibs and the Pitivi-specific GI overrides only exist inside the sandbox.

## Common commands

All of these assume you are inside `(ptv-flatpak)`:

- `pitivi` — run Pitivi from the working tree (`PITIVI_DEVELOPMENT=1` is set automatically).
- `setup` — one-time: create `mesonbuild/` (`mkdir mesonbuild; ptvenv meson mesonbuild/ --prefix=/app --libdir=lib`).
- `build` — alias for `ninja -C mesonbuild/`. Required after editing C code in `pitivi/coptimizations/`, the `bin/pitivi.in` launcher, or `pitivi/configure.py.in` (these regenerate `.py` files).
- `binstall` — `ninja -C mesonbuild/ install`. Needed to see translations or anything that has to be installed into the sandbox prefix.
- `ptvtests` — run the unit test suite (wraps `gst-validate-launcher tests/ptv_testsuite.py --dump-on-failure`).
- `ptvtests -L` — list all tests.
- `ptvtests -t <pattern>` — run a subset. The pattern matches module / class / method substrings, e.g. `ptvtests -t test_project`, `ptvtests -t TestProjectManager`, `ptvtests -t test_loading_missing_project_file`.
- `ptvtests --timeout-factor 10` — useful when a test legitimately needs more time (e.g. while debugging).
- `ptvenv tests/validate-tests/runtests` — run integration tests (GstValidate scenarios under `tests/validate-tests/scenarios/`).
- `pre-commit run --all-files` — run all configured linters (also runs automatically on commit via the symlinked `pre-commit.hook`).

`PITIVI_VSCODE_DEBUG=1 pitivi` (or the same with `ptvtests`) starts a `debugpy` listener on port 5678 and waits for an attach.

## Linting

The pre-commit pipeline (configured in `.pre-commit-config.yaml`) runs: trailing-whitespace / EOF / encoding-pragma fixers, `reorder-python-imports`, `pydocstyle`, `flake8`, `mypy` (only on `pitivi/autoaligner.py`, `pitivi/clipproperties.py`, `pitivi/timeline/timeline.py`), `pylint` (config in `pylint.rc`), and `yamllint`. The pre-commit hook is automatically symlinked when entering the dev env, and it requires `PITIVI_REPO_DIR` to be set (i.e. the dev env must have been entered) — committing from a plain shell will fail.

## Code architecture

Pitivi is a Python/GTK frontend on top of GStreamer Editing Services (GES). It is **not** a self-contained Python app: it is glued together by GObject signals across several layers, all loaded via PyGObject (`gi.repository`).

- **Backend stack** (not in this repo): GStreamer → Non-Linear Engine (gnonlin/nle) → GES → Pitivi. GES owns the timeline model, asset management, and rendering pipeline. Most "model" objects you'll see in code (`GES.Timeline`, `GES.Layer`, `GES.Clip`, `GES.TrackElement`, `GES.Project`) come from GES.
- **Frontend** is the `pitivi/` Python package. Entry point is `bin/pitivi.in` (built into `bin/pitivi`), which sets paths, calls `pitivi.check.initialize_modules()` and `check_requirements()`, then runs `pitivi.application.Pitivi` (a `Gtk.Application`).
- `pitivi/check.py` is the canonical list of hard and soft dependencies — read this if you need to know what versions/plugins Pitivi requires.
- `pitivi/application.py` wires together the long-lived singletons hung off the `Pitivi` app object: `ProjectManager`, `EffectsManager`, `PluginManager`, `GlobalSettings`, `ShortcutsManager`, `UndoableActionLog`, `ProjectObserver`, `System`, `ThreadMaster`. Anything that needs cross-cutting state takes the `app` reference.
- The UI is split into **perspectives** (`greeterperspective.py`, `editorperspective.py`, `trackerperspective.py`) hosted by `MainWindow` (`mainwindow.py`). The greeter is the project picker; the editor is the timeline + viewer + library + clip props.
- `pitivi/timeline/` contains the timeline UI (canvas, layers, clip elements, ruler, previewers, markers). `pitivi/viewer/` is the preview area with overlays. `pitivi/clip_properties/` holds the per-clip property panels.
- `pitivi/undo/` implements the undo/redo system. Edits to GES objects are observed by `ProjectObserver` and converted into `UndoableAction`s pushed onto `UndoableActionLog`. When adding features that mutate the timeline, register matching undo support here.
- `pitivi/utils/` is a grab bag of cross-cutting helpers — note `loggable.py` (logging mixin used everywhere via `Loggable`), `pipeline.py` (Pitivi's wrapper around the GES rendering pipeline), `proxy.py` (proxy-asset/transcoding strategy), `validate.py` (action handlers for the integration scenarios), `timeline.py` (the `Zoomable` mixin and selection helpers).
- C extensions live in `pitivi/coptimizations/` (currently `renderer.c` for the audio-envelope rendering of audio clips). Built by Meson into `pitivi/timeline/renderer.so`. Edit → `build` → re-run.
- Plugins live under `plugins/`; the in-tree console plugin is the reference. They are loaded by `pitivi/pluginmanager.py`.

## Coding conventions

These are enforced by review and linters — they will save round-trips:

- **Naming**: `snake_case` for functions, methods, attributes. Single underscore prefix = protected, double underscore = private.
- **Callbacks** for GObject signals: name them `__<thing>_<event>_cb` (private) and prefix unused arguments with `unused_` (e.g. `def __pad_added_cb(self, unused_element, pad):`).
- Docstrings follow the Google Python Style Guide (see `docs/Coding_style_guide.md`).
- Keep lines reasonable; PEP-8 with `E402,E501,E722,F401,F841,W504` ignored in flake8.

## Tests

- Unit tests: `tests/test_*.py`. New tests should use the helpers in `tests/common.py` (see e.g. `common.create_pitivi_mock`, `common.create_timeline_container`). UI tests rely heavily on `unittest.mock`.
- Pair logic file → test file by name: `pitivi/clip_properties/color.py` → `tests/test_clipproperties_color.py`. Undo-related logic for an area is usually covered both in its own file and in `tests/test_undo_*`.
- Integration tests are GstValidate `.scenario` files under `tests/validate-tests/scenarios/`, driven by handlers in `pitivi/utils/validate.py`. New `.scenario` files are auto-generated each time Pitivi runs (see `application.write_action`).

## Reference

More detail in `docs/`: `HACKING.md`, `Testing.md`, `Debugging.md`, `Architecture.md`, `Coding_style_guide.md`, `GES.md`, `Plugins.md`.
