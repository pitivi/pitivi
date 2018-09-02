# How to make a release

Ideally these instructions are in line with the [GNOME releasing process](https://live.gnome.org/MaintainersCorner/Releasing).

We make two types of releases:
- regular releases, when we have new features or improvements, and
- "smaller" bug-fix releases, when a regular release needs patching.

The regular releases have the version number X.YY, and the bug-fix
releases have the version number X.YY.Z, where Z is hopefully a relatively small
number (1, 2, 3...).

Most of the steps below should be done in the [development environment](HACKING.md): `$ source bin/pitivi-env` -> `(ptv-flatpak) $`

1. Check [GitLab](https://gitlab.gnome.org/GNOME/pitivi/milestones)
    * Make sure there are no significant issues open against the current milestone.
    * Move the remaining open issues somewhere else, for example to the next milestone.
    * Close the current milestone.

2. Make sure we depend on the latest GStreamer. This should be done as soon as GStreamer makes a release.
    * Find the latest tag in https://cgit.freedesktop.org/gstreamer/gstreamer/
    * See our current requirement for Gst at the bottom in [check.py](../pitivi/check.py)
    * If they are different, update the files which contain the old version, for example: `$ git grep "1\.8\.2"` and `$ git commit -a -m "Use GStreamer <gstreamer-version>"`

3. Check your local repository:
    * Make sure your sandbox is using the latest GStreamer release: `$ ptvenv --update --gst-version=<gst-version>`
    * Check `$ git status` does not show any change

4. Make sure the tests pass:
   ```
   $ ninja -C mesonbuild/ test
   ```
 <!-- * `$ make validate` FIXME! -->

5. Update the following files:
    * [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build):
If doing a bugfix release, add or increase the micro.
If doing a regular release, bump YY up and remove the micro from
the version number, for example: 0.97.1 -> 0.98. Normally this is the
same as the name of the Phabricator milestone you just archived.
     * [RELEASE](https://gitlab.gnome.org/GNOME/pitivi/blob/master/RELEASE):
Update the short version of the release notes.
To get the list of contributors: `$ git shortlog -s -n <previous-tag>..`
To get the list of translators: `$ for i in po/*.po help/*; do echo $i; git shortlog -s <previous-tag>.. $i; done`
     * [NEWS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/NEWS):
A shorter version of RELEASE, with the exec summary of changes.
     * [AUTHORS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/AUTHORS):
If there are new maintainers.

6. Commit the changes: `$ git commit -a -m "Release <version-number>"`

7. Create the distribution archive:
   ```
   $ ninja -C mesonbuild/ dist
   $ ls -l mesonbuild/meson-dist/*.tar.*
   ```
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

8. Create a tag and push it to the official repository. The TAG must always include the micro. This means when doing a regular release with version number X.YY, the TAG is X.YY.0. When doing a bug-fix release, the version number already includes a micro, so it's all fine.
   ```
   $ git tag -a <TAG> -m "Release <version-number>"
   $ git push origin <TAG>
   ```
   We use tag X.YY.0 instead of X.YY because we want to have the option of later creating the X.YY branch to the official repository, since it's not possible to have both a tag and a branch with the same name. This branch would gather backported fixes and be used for doing future X.YY.Z bug-fix releases.

9. Publish the archive on Gnome:
   ```
   $ scp mesonbuild/meson-dist/pitivi-X.YY.Z.tar.xz GNOME-USER@master.gnome.org:
   $ ssh GNOME-USER@master.gnome.org -t ftpadmin install pitivi-X.YY.Z.tar.xz
   ```
   The tarball will appear on https://download.gnome.org/sources/pitivi/X.YY/pitivi-X.YY.Z.tar.xz

10. Send out an announcement mail to:
    * gstreamer-devel@lists.freedesktop.org
    * gnome-i18n@gnome.org (thanking translators)

11. On pitivi.org, update "releases.txt" for the app's update notification feature

12. Bump the Z in the version number in [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build), for example if it was a regular release: 0.98 -> 0.98.1 or if it was a bug-fix release: 0.97.1 -> 0.97.2, and `$ commit -a -m "Back to development"`
