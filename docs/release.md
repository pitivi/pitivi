# How to make a release

Ideally these instructions are in line with the [GNOME releasing process](https://live.gnome.org/MaintainersCorner/Releasing).

We make two types of releases:
- regular releases, when we have new features or improvements, and
- "smaller" bug-fix releases, when a regular relese needs patching.

The regular releases have the version number X.YY, and the bug-fix
releases have the version number X.YY.Z, where Z is hopefully a relatively small
number (1, 2, 3...).

Most of the steps below should be done in the [development environment](HACKING.md): `$ source bin/pitivi-env` -> `(ptv-flatpak) $`

1. Check [GitLab](https://gitlab.gnome.org/GNOME/pitivi/milestones)
    * Make sure there are no significant issues open against the current milestone.
    * Move the remaining open issues somewhere else, for example to the next milestone.
    * Close the current milestone.

2. Check your local dev env:
    * Make sure your sandbox is using the latest GStreamer release: `$ ptvenv --update`
    * Check `$ git status` does not show any change

3. Update the following files:
    * [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build):
If doing a bugfix release, add or increase the micro.
If doing a regular release, bump YY up and remove the micro from
the version number, for example: 0.97.1 -> 0.98. Normally this is the
same as the name of the Phabricator milestone you just archived.
     * [data/org.pitivi.Pitivi.appdata.xml.in](https://gitlab.gnome.org/GNOME/pitivi/blob/master/data/org.pitivi.Pitivi.appdata.xml.in):
Add a new release tag with the exec summary of changes.
     * [NEWS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/NEWS):
Copy the exec summary of changes also here. This ends up in the `.news` file at [download.gnome.org/sources/pitivi](https://download.gnome.org/sources/pitivi/).
     * [AUTHORS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/AUTHORS):
If there are new maintainers.

4. Commit the changes: `$ git commit -a -m "Release <version-number>"`

5. Create the distribution archive:
   ```
   $ ninja -C mesonbuild/ dist
   $ ls -l mesonbuild/meson-dist/*.tar.*
   ```
   On an X system, `ninja dist` might not work because the unit tests fail because of X. In this case, stop X and use a fake X server: `xvfb-run ninja -C mesonbuild/ dist`.

   Install it on a real system and give it a spin. For example on Archlinux:
   ```
   $ cd /tmp
   $ asp checkout pitivi
   $ cd /tmp/pitivi/repos/community-x86_64/
   $ cp .../pitivi-X.YY.Z.tar.xz .
   $ vim PKGBUILD
   ... Update "pkgver",
   ... Make sure "source" ends in .tar.xz
   ... Update "sha256sums"
   $ makepkg
   $ makepkg -i
   $ pitivi
   ```

6. Create a tag and push it to the official repository. The TAG must always include the micro. This means when doing a regular release with version number X.YY, the TAG is X.YY.0. When doing a bug-fix release, the version number already includes a micro, so it's all fine.
   ```
   $ git tag -a <TAG> -m "Release <version-number>"
   $ git push origin <TAG>
   ```
   We use tag X.YY.0 instead of X.YY because we want to have the option of later creating the X.YY branch to the official repository, since it's not possible to have both a tag and a branch with the same name. This branch would gather backported fixes and be used for doing future X.YY.Z bug-fix releases.

7. Publish the archive on Gnome:
   ```
   $ scp mesonbuild/meson-dist/pitivi-X.YY.Z.tar.xz GNOME-USER@master.gnome.org:
   $ ssh GNOME-USER@master.gnome.org -t ftpadmin install pitivi-X.YY.Z.tar.xz
   ```
   The tarball will appear on https://download.gnome.org/sources/pitivi/X.YY/pitivi-X.YY.Z.tar.xz

8. Spread the word about the release
    * Send an [email](https://lists.freedesktop.org/archives/gstreamer-devel/2017-September/065566.html) to gstreamer-devel@lists.freedesktop.org
    * Send an [email](https://mail.gnome.org/archives/gnome-i18n/2017-September/msg00136.html) to gnome-i18n@gnome.org thanking translators.
    * [Archlinux](https://www.archlinux.org/packages/community/x86_64/pitivi/), click "Flag Package Out-of-Date".
    * [Debian](https://packages.debian.org/pitivi), click the "unstable" Debian version and look for "maintainer".
    * [Fedora](https://apps.fedoraproject.org/packages/pitivi), look for Point of Contact.

9. Update http://www.pitivi.org/releases.txt for the app's update notification feature

10. Bump the Z in the version number in [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build), for example if it was a regular release: 0.98 -> 0.98.1 or if it was a bug-fix release: 0.97.1 -> 0.97.2, and `$ commit -a -m "Back to development"`
