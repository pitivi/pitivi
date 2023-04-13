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

The `hotdoc` and `matplotlib` packages are quite complex, needing additional
build dependencies which have to be installed beforehand. Jan 2021 it's much
easier to install the compiled packages instead of the source packages. When
upstream makes it easier to use source packages we should switch.

Note, we use a custom `flatpak-pip-generator` which downloads the compiled
Python packages. The upstream version downloads only the source packages, for
security reasons.

```
$ git clone git@github.com:aleb/flatpak-builder-tools.git
```

Create a venv to be able to run flatpak-build-generator:

```
$ python3 -m venv /tmp/venv1
$ /tmp/venv1/bin/pip3 install requirements-parser setuptools
```

Change the current dir:

```
$ cd build/flatpak
$ P=/tmp/venv1/bin/python3
$ G=/.../flatpak-builder-tools/pip/flatpak-pip-generator
```

## Updating runtime dependencies

```
$ $P $G --runtime org.gnome.Sdk/x86_64/46 librosa
$ $P $G --runtime org.gnome.Sdk/x86_64/46 matplotlib
```

## Updating the development tools

```
$ $P $G --runtime org.gnome.Sdk/x86_64/46 'wheezy.template<=3.1.0' nose setuptools_git setuptools_pep8 sphinx hotdoc
$ mv python3-modules.json python3-hotdoc.json
$ $P $G --runtime org.gnome.Sdk/x86_64/46 ipdb
```

Note: `wheezy.template 3.2.2` produces an error, that's why we avoid it:
```
(ptv-flatpak) $ hotdoc
Traceback (most recent call last):
[...]
  File "src/wheezy/template/typing.py", line 6, in init wheezy.template.typing
    All subscripted types like X[int], Union[int, str] are generic aliases.
TypeError: 'type' object is not subscriptable

```

## Updating the pre-commit framework

```
$ $P $G --runtime org.gnome.Sdk/x86_64/46 pre-commit
$ $P $G --runtime org.gnome.Sdk/x86_64/46 setuptools-scm 'pylint<=2.13.5'
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
$ flatpak run --user --command=bash --devel org.gnome.Sdk/x86_64/46
[📦 org.gnome.Sdk ~]$ which python3
/usr/bin/python3
```
