---
short-description: How to update the Python dependencies
...

# Python dependencies

Pitivi has only two Python runtime dependencies: `librosa` and `matplotlib`, but
in the development sandbox we install quite a few Python tools.

Each Python package has its own `python3-*.json` file in
[build/flatpak](https://gitlab.gnome.org/GNOME/pitivi/-/tree/master/build/flatpak),
generated with
[flatpak-pip-generator](https://github.com/aleb/flatpak-builder-tools/tree/master/pip):

```
$ git clone git@github.com:aleb/flatpak-builder-tools.git
```

Note, we use a custom `flatpak-pip-generator` which downloads the compiled
Python packages. The upstream version downloads only the source packages, for
security reasons.

The `hotdoc` and `matplotlib` packages are quite complex, needing additional
build dependencies which have to be installed beforehand. Jan 2021 it's much
easier to install the compiled packages instead of the source packages. When
upstream makes it easier to use source packages we should switch.

## Updating runtime dependencies

```
$ cd build/flatpak
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 librosa
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 matplotlib
```

## Updating the development tools

```
$ cd build/flatpak
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 nose setuptools_git setuptools_pep8 sphinx hotdoc
$ mv python3-modules.json python3-hotdoc.json
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 ipdb
```

## Updating the pre-commit framework

```
$ cd build/flatpak
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 pre-commit
$ python3 flatpak-pip-generator --runtime org.gnome.Sdk/x86_64/44 setuptools-scm 'pylint<=2.13.5'
```

## Updating your local sandbox

After you update the json files, try out the build by updating your local
development environment:

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv --update
```

If errors happen, you can inspect the SDK by launching `bash` in a sandbox, for
example:

```
$ flatpak run --user --command=bash --devel org.gnome.Sdk/x86_64/44
[📦 org.gnome.Sdk ~]$ python3 --version
Python 3.10.6
```
