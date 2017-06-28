---
title: Releasing
short_description: How to make a release
...

# How to make a release

See also https://live.gnome.org/MaintainersCorner/Releasing

Besides the regular releases, you can also make smaller bug-fix releases.
The regular releases have the version number X.YY, and the bug-fix
releases have the version number X.YY.Z, where Z is a relatively small
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

 3. Check your local repository
   * Make sure your sandbox is using the latest GStreamer release: `$ ptvenv --update --gst-version=<gst-version>`
   * `$ git status` does not show any change
   * `$ configure` is all green

 4. Make sure the tests pass
   * `$ ninja test`
   <!-- * `$ make validate` FIXME! -->

 5. Update the following files:
   * [meson.build](../meson.build):
Only if doing a regular release. Bump YY up and remove the micro from
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

 7. Create the distribution archive
   * `$ cd mesonbuild && ninja dist && cd .. && ls *.tar.gz`
   * Install it on your favorite system, check that it works.

 8. Create a tag: `$ git tag -a <version-number> -m "Release <version-number>"`
 9. Push the tag to the official repository: `$ git push origin <version-number>`

 10. Publish the archive
   * `$ scp pitivi-X.YY.ZZ.tar.gz master.gnome.org:`
   * On master.gnome.org, run `$ ftpadmin install pitivi-X.YY.ZZ.tar.gz`
     The tarball will appear as `.tar.xz` on https://download.gnome.org/sources/pitivi/X.YY/ (also visible on http://ftp.gnome.org/pub/gnome/sources/pitivi/X.YY/)

 11. Send out an announcement mail to:
     * gstreamer-devel@lists.freedesktop.org
     * gnome-i18n@gnome.org (thanking translators)

 12. On pitivi.org, update "releases.txt" for the app's update notification feature

 13. Bump the Z in the version number in [meson.build](../meson.build), for example if it was a regular release: 0.98 -> 0.98.1 or if it was a bug-fix release: 0.97.1 -> 0.97.2, and `$ commit -a -m "Back to development"`
