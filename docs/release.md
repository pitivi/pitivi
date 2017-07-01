# How to make a release

Ideally these instructions are in line with the [GNOME releasing process](https://live.gnome.org/MaintainersCorner/Releasing).

We make two types of releases:
- regular releases, when we have new features or improvements, and
- "smaller" bug-fix releases, when a regular relese needs patching.

The regular releases have the version number X.YY, and the bug-fix
releases have the version number X.YY.Z, where Z is hopefully a relatively small
number (1, 2, 3...).

Most of the steps below should be done in the [development environment](HACKING.md): `$ source bin/pitivi-env` -> `(ptv-flatpak) $`

 1. Check [Phabricator](https://phabricator.freedesktop.org/tag/pitivi/)
   * Make sure there is no open 'blocker' task against the current milestone.
   * Move the other open tasks somewhere else, for example to the next milestone.
   * Archive the current milestone.

 2. Make sure we depend on the latest GStreamer. This should be done as soon as GStreamer makes a release.
   * Find the latest tag in https://cgit.freedesktop.org/gstreamer/gstreamer/
   * See our current requirement for Gst at the bottom in [check.py](../pitivi/check.py)
   * If they are different, update the files which contain the old version, for example: `$ git grep "1\.8\.2"` and `$ git commit -a -m "Use GStreamer <gstreamer-version>"`

 3. Check your local repository:
   * Make sure your sandbox is using the latest GStreamer release: `$ ptvenv --update --gst-version=<gst-version>`
   * Install git-archive-all in your sandbox to be able to create the archive to be distributed: `$ build/flatpak/py-configure --module=git-archive-all && make install`
   * Check `$ git status` does not show any change
   * Check `$ ptvenv ./configure` is all green

 4. Make sure the tests pass:
  ```
  $ ninja -C mesonbuild/ test
  ```
 <!-- * `$ make validate` FIXME! -->

 5. Update the following files:
   * [meson.build](../meson.build):
If doing a bugfix release, add or increase the micro.
If doing a regular release, bump YY up and remove the micro from
the version number, for example: 0.97.1 -> 0.98. Normally this is the
same as the name of the Phabricator milestone you just archived.
   * [RELEASE](../RELEASE):
Update the short version of the release notes.
To get the list of contributors: `$ git shortlog -s -n <previous-tag>..`
To get the list of translators: `$ for i in po/*.po help/*; do echo $i; git shortlog -s <previous-tag>.. $i; done`
   * [NEWS](../NEWS):
A shorter version of RELEASE, with the exec summary of changes.
   * [AUTHORS](../AUTHORS):
If there are new maintainers.

 6. Commit the changes: `$ git commit -a -m "Release <version-number>"`

 7. Create the distribution archive, install it on your favorite system and check that it works:
   * `$ ninja -C mesonbuild/ dist && ls *.tar.gz`
   * For Archlinux try:
 ```
 $ cd /tmp
 $ asp checkout pitivi
 $ cd /tmp/pitivi/repos/community-x86_64/
 $ rm -rf .git  # Without this, ./configure is confused re version number.
 $ cp .../pitivi-X.YY.Z.tar.gz .
 $ vim PKGBUILD
 ... Update "pkgver",
 ... Make sure "source" ends in .tar.gz
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
   We use tag X.YY.0 instead of X.YY because we want to have the option of later creating the X.YY branch to the official repository, since it's not possible to have both a tag and a branch with the same name. This branch would be used to gather backported fixes and be the official branch for doing a X.YY.Z bug-fix release.

 10. Publish the archive
   * `$ scp pitivi-X.YY.Z.tar.gz USER@master.gnome.org:`
   * On master.gnome.org, run `$ ftpadmin install pitivi-X.YY.Z.tar.gz`
     The tarball will appear as `.tar.xz` on https://download.gnome.org/sources/pitivi/X.YY/ (also visible on http://ftp.gnome.org/pub/gnome/sources/pitivi/X.YY/)

 11. Send out an announcement mail to:
     * gstreamer-devel@lists.freedesktop.org
     * gnome-i18n@gnome.org (thanking translators)

 12. On pitivi.org, update "releases.txt" for the app's update notification feature

 13. Bump the Z in the version number in [meson.build](../meson.build), for example if it was a regular release: 0.98 -> 0.98.1 or if it was a bug-fix release: 0.97.1 -> 0.97.2, and `$ commit -a -m "Back to development"`
