---
short-description: How to update the Python dependencies
...

# Python dependencies

Pitivi has only two Python runtime dependencies: `librosa` and `matplotlib`, but
in the development sandbox we install quite a few Python tools useful for
development.

Each Python package has its own `python3-*.json` file in
[build/flatpak](https://gitlab.gnome.org/GNOME/pitivi/-/tree/master/build/flatpak),
generated with [build/flatpak/update_deps.py](https://gitlab.gnome.org/GNOME/pitivi/-/tree/master/build/flatpak).
The script uses a custom [flatpak-pip-generator](https://github.com/aleb/flatpak-builder-tools/tree/master/pip)
which downloads the compiled Python packages.

The original `flatpak-pip-generator` downloads only source packages, for extra
security. But some packages are very complex, such as `hotdoc` (dev docs website
generator) and `matplotlib` (used to draw keyframes lines on the clips). These
need additional build dependencies which have to be installed beforehand.

TL/DR: As of Jan 2021 it's much easier to install the compiled packages instead
of the source packages. When [upstream](https://github.com/flatpak/flatpak-builder-tools/commits/master/pip)
makes it easier to use source packages we should switch back.

## Updating the Python deps

To update the Python deps, all you have to do is to run:
```
$ . bin/pitivi-env
(ptv-flatpak) $ build/flatpak/update_deps.py
```

## Updating your local sandbox

After the json files have been successfully updated, try out the build by
updating your local development environment:

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv --update
(ptv-flatpak) $ pitivi
```

If errors happen, you can inspect the SDK by launching `bash` in a sandbox, for
example:

```
$ flatpak run --user --command=bash --devel org.gnome.Sdk/x86_64/46
[📦 org.gnome.Sdk ~]$ which python3
/usr/bin/python3
```
