# Install with flatpak

The Pitivi community supports a [flatpak](http://flatpak.org/)
repository to let users install the latest Pitivi releases. This is the
official, recommended way of installing Pitivi on Linux. The repository
contains only 64-bit builds.

If you see problems, come to our [IRC
channel](http://www.pitivi.org/?go=contact) or [file a
bug](Bug_reporting.md).

## Getting Flatpak

You can get information about how to install flatpak for your
distribution [here](http://flatpak.org/getting.html).

You need to log out/in again after installing flatpak for apps to show
up in menus. Until you log out/in, the flatpak data directories aren't
part of your desktop environment's search path. This needs to be done
only one time.

## Installing Pitivi

To install the latest stable Pitivi release, run as a normal user (no
root nor sudo):

  `$ flatpak install --user `[`https://flathub.org/repo/appstream/org.pitivi.Pitivi.flatpakref`](https://flathub.org/repo/appstream/org.pitivi.Pitivi.flatpakref)

We also provide latest development snapshot toward what is going to become `Pitivi 1.0`, you can install with:

  `$ flatpak install --user `[`http://flatpak.pitivi.org/pitivi.flatpakref`](http://flatpak.pitivi.org/pitivi.flatpakref)`

### Troubleshooting

If your flatpak version is less than 0.8, you need to run instead:

` $ flatpak --version`\
` $ curl `[`https://git.gnome.org/browse/pitivi/plain/build/flatpak/pitivi-flatpak`](https://git.gnome.org/browse/pitivi/plain/build/flatpak/pitivi-flatpak)` -Sso pitivi-flatpak`\
` $ chmod +x pitivi-flatpak`\
` $ ./pitivi-flatpak --branch=`**`stable`**` --update`

When the script finishes installing (or updating), it launches Pitivi.

## Installing Pitivi master (development version)

To install the development version as a separate application called
“(Rolling) Pitivi”, run in a terminal:

` $ flatpak install --user `[`http://flatpak.pitivi.org/pitivi-master.flatpakref`](http://flatpak.pitivi.org/pitivi-master.flatpakref)

You might want to use Pitivi master to contribute and help us test
Pitivi, or if a specific bug which annoys you is fixed in master, etc.

## Running Pitivi

You can now launch Pitivi from your applications menu as any other
installed application.

You can also re run the installer which launches Pitivi after updating
to the latest version.

To see if warning or error messages are printed in the console, run:

` $ flatpak run org.pitivi.Pitivi//stable`

If for some reason you need to use an older Pitivi version, run:

` $ flatpak run org.pitivi.Pitivi//0.96`

## Updating Pitivi

To update Pitivi to the latest version you can just run again the
installer the same way as before.

Alternatively, update by using directly flatpak:

` $ flatpak --user update org.pitivi.Pitivi`

If a new version is fetched, it will be made current.

## Uninstalling Pitivi

If your software manager doesn't allow this yet, run the command below:

` $ flatpak --user uninstall org.pitivi.Pitivi stable`

## Install GStreamer vaapi support

In the sandbox gstreamer-vaapi is installed but it requires the
org.freedesktop.Platform.VAAPI.Intel extension to be installed.

As the support is experimental, you need to set PITIVI_UNSTABLE_FEATURES
to enable them: `flatpak run --env=PITIVI_UNSTABLE_FEATURES=vaapi org.pitivi.Pitivi`.
