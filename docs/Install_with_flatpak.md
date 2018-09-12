# Install with flatpak

The Pitivi community supports a [flatpak](http://flatpak.org/)
repository to let users install the latest Pitivi releases. This is the
official, recommended way of installing Pitivi on Linux. The repository
contains only 64-bit builds.

If you see problems, come to our [IRC
channel](http://www.pitivi.org/?go=contact) or [file a
bug](Bug_reporting.md).

## Getting Flatpak

See the flatpak website for [how to install flatpak](https://flatpak.org/setup/)
for your distribution.

You need to log out/in again after installing flatpak for apps to show
up in menus. Until you log out/in, the flatpak data directories aren't
part of your desktop environment's search path. This needs to be done
only one time.

## Installing Pitivi

Currently there are no less than three options for installing Pitivi. Each
can be installed by running the commands below as normal user, no root/sudo
needed.

- **latest release**, for production work:

```
$ flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
$ flatpak install flathub org.pitivi.Pitivi
```

- **1.0 development snapshot**, for testing the next release:

```
$ flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
$ flatpak install flathub org.gnome.Platform//3.28
$ flatpak install http://flatpak.pitivi.org/pitivi.flatpakref
```

- **master development snapshot**, which includes the latest features:

```
$ flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
$ flatpak install flathub org.gnome.Platform//3.28
$ flatpak install http://flatpak.pitivi.org/pitivi-master.flatpakref
```

## Running Pitivi

You can now launch Pitivi from your applications menu as any other
installed application.

You can also re run the installer which launches Pitivi after updating
to the latest version.

To see if warning or error messages are printed in the console, run:

```
$ flatpak run org.pitivi.Pitivi//stable
```

If for some reason you need to use an older Pitivi version, run:

```
$ flatpak install org.pitivi.Pitivi//0.96
$ flatpak run org.pitivi.Pitivi//0.96
```

## Updating Pitivi

If your software manager doesn't allow this yet, updating manually by running:

```
$ flatpak update org.pitivi.Pitivi
```

If a new version is fetched, it will be made current.

## Uninstalling Pitivi

If your software manager doesn't allow this yet, run the command below:

```
$ flatpak uninstall org.pitivi.Pitivi
```

## Install GStreamer vaapi support

In the sandbox gstreamer-vaapi is installed but it requires the
`org.freedesktop.Platform.VAAPI.Intel` extension to be installed.

As the support is experimental, you need to set `PITIVI_UNSTABLE_FEATURES`
to enable them:
```
$ flatpak run --env=PITIVI_UNSTABLE_FEATURES=vaapi org.pitivi.Pitivi
```
