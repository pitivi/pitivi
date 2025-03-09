# Install with flatpak

We release every few months, meaning you most likely want to install the latest
release [from Flathub](https://flathub.org/apps/details/org.pitivi.Pitivi).

To try out the latest development branch, get the development snapshot from our
own [flatpak](http://flatpak.org/) repository. The repository contains only
64-bit builds.

Please [file an issue](Bug_reporting.md) if you have exact steps to reproduce
the bug. Feel free to [contact us](https://www.pitivi.org/contact/) if you see
any problems.

## Getting Flatpak

See the flatpak website for [how to install flatpak](https://flatpak.org/setup/)
for your distribution.

You need to log out/in again after installing flatpak for apps to show
up in menus. Until you log out/in, the flatpak data directories aren't
part of your desktop environment's search path. This needs to be done
only one time.

## Installing Pitivi

Run the commands below as normal user, no root/sudo needed.

### Latest release

Suited for production work.

```
$ flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
$ flatpak install flathub org.pitivi.Pitivi
```

### Development snapshot

Built daily out of the development branch.

```
$ flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
$ flatpak install flathub org.gnome.Platform//47
$ flatpak install http://flatpak.pitivi.org/pitivi-master.flatpakref
```

## Running Pitivi

You can now launch Pitivi from your applications menu as any other
installed application.

You can also re run the installer which launches Pitivi after updating
to the latest version.

To see if warning or error messages are printed in the console, run:

```
$ flatpak run org.pitivi.Pitivi//stable
```

If for some reason you need to use an older Pitivi version, run:

```
$ flatpak install org.pitivi.Pitivi//0.96
$ flatpak run org.pitivi.Pitivi//0.96
```

## Updating Pitivi

If your software manager doesn't allow this yet, update manually by running:

```
$ flatpak update org.pitivi.Pitivi
```

If a new version is fetched, it will be made current.

## Uninstalling Pitivi

If your software manager doesn't allow this yet, run the command below:

```
$ flatpak uninstall org.pitivi.Pitivi
```

## Install GStreamer vaapi support

In the sandbox gstreamer-vaapi is installed but it requires the
`org.freedesktop.Platform.VAAPI.Intel` extension to be installed.
