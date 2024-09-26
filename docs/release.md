---
short-description: How to make a new release
...

# Making a release

Ideally these instructions are in line with the [GNOME releasing
process](https://live.gnome.org/MaintainersCorner/Releasing).

We make two types of releases:
- regular releases, when we have new features or improvements, and
- "smaller" bug-fix releases, when a regular release needs patching.

The regular releases have the version number YYYY.MM, and the bug-fix releases
have the version number YYYY.MM.Z, where Z is hopefully a relatively small
number (1, 2, 3...).

Most of the steps below should be done in the [development
environment](HACKING.md):

```
$ source bin/pitivi-env
(ptv-flatpak) $ _
```

0. Freeze the strings
    * Post to [gnome-i18n](https://discourse.gnome.org/tag/i18n)
    to inform the translators the strings have been frozen and that
    in **one week** the release will be cut.
    * It would be good to start preparing a blogpost already.

1. Check [GitLab](https://gitlab.gnome.org/GNOME/pitivi/-/milestones)
    * Make sure there are no significant issues open against the current milestone.
    * Move the remaining open issues somewhere else, for example to the next milestone.
    * Close the current milestone.

2. Check your local dev env:
    * Make sure your sandbox is using the latest GStreamer release:
      ```
      $ ptvenv --update
      ```

    * Check there are no uncommitted changes:
      ```
      $ git status
      ```

3. Update the following files:
    * [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build):
If doing a bugfix release, make sure the micro (Z) from the version number has
been increased. If doing a regular release, update the version number with the
current year and month and remove the micro, if any. Normally this is the
same as the name of the GitLab milestone you just archived.
     * [NEWS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/NEWS):
Compose the exec summary of changes, at the top. This ends up in the `.news`
file at [download.gnome.org/sources/pitivi](https://download.gnome.org/sources/pitivi/).
     * [data/org.pitivi.Pitivi.appdata.xml.in](https://gitlab.gnome.org/GNOME/pitivi/blob/master/data/org.pitivi.Pitivi.appdata.xml.in):
Run `appstreamcli news-to-metainfo NEWS data/org.pitivi.Pitivi.appdata.xml.in`.
     * [AUTHORS](https://gitlab.gnome.org/GNOME/pitivi/blob/master/AUTHORS):
If there are new maintainers.

4. Commit the changes:
   ```
   $ git commit -a -m "Release <version-number>"
   ```

5. Create the distribution archive:
   ```
   $ ninja -C mesonbuild/ dist
   $ ls -l mesonbuild/meson-dist/*.tar.*
   ```
   On an X system, `ninja dist` might not work because the unit tests fail
   because of X. In this case, stop X with `sudo systemctl stop gdm` and use a
   fake X server: `xvfb-run /.../pitivi/build/flatpak/pitivi-flatpak ninja -C mesonbuild/ dist`.

   Install it on a real system and give it a spin. For example on Archlinux:
   ```
   $ cd /tmp
   $ asp update pitivi
   $ asp checkout pitivi
   $ cd /tmp/pitivi/repos/community-x86_64/
   $ cp .../pitivi-YYYY.MM.Z.tar.xz .
   $ vim PKGBUILD
   ... Update "pkgver"
   ... Make sure the filename at the end of "source" matches the copied file
   ... Update "sha256sums"
   $ makepkg
   $ makepkg -i
   $ pitivi
   ```

6. Create a tag and push it to the official repository. The TAG must always include the micro. This means when doing a regular release with version number YYYY.MM, the TAG is YYYY.MM.0. When doing a bug-fix release, the version number already includes a micro, so it's all fine.
   ```
   $ git push origin master
   $ git tag -a <TAG> -m "Release <version-number>"
   $ git push origin <TAG>
   ```
   We use tag YYYY.MM.0 instead of YYYY.MM because we want to have the option of
   later creating the YYYY.MM branch to the official repository, since it's not
   possible to have both a tag and a branch with the same name. This branch
   would gather backported fixes and be used for doing future YYYY.MM.Z bug-fix
   releases.

7. Publish the archive on Gnome:
   ```
   $ scp mesonbuild/meson-dist/pitivi-YYYY.MM.tar.xz GNOME-USER@master.gnome.org:
   $ ssh GNOME-USER@master.gnome.org -t ftpadmin install pitivi-YYYY.MM.tar.xz
   ```
   The tarball will appear on
   https://download.gnome.org/sources/pitivi/YYYY.MM/pitivi-YYYY.MM.tar.xz

8. Spread the word about the release
    * Send an [email](https://lists.freedesktop.org/archives/gstreamer-devel/2017-September/065566.html) to gstreamer-devel@lists.freedesktop.org
    * Reply to the connected string freeze [post](https://discourse.gnome.org/tag/i18n), expressing gratitude to the translators.
    * [Archlinux](https://www.archlinux.org/packages/community/x86_64/pitivi/), click "Flag Package Out-of-Date".
    * [Debian](https://packages.debian.org/pitivi), click the "unstable" Debian version and look for "maintainer".
    * [Fedora](https://packages.fedoraproject.org/pkgs/pitivi/pitivi/), look for "You can contact the maintainers of this package via email at".

9. Update the [releases.txt](https://www.pitivi.org/releases.txt) file for the
   app's update notification feature in
   [pitivi-web](https://gitlab.gnome.org/Infrastructure/pitivi-web/-/blob/master/static/releases.txt).

10. Bump the Z in the version number in
    [meson.build](https://gitlab.gnome.org/GNOME/pitivi/blob/master/meson.build),
    for example if it was a regular release: `2020.09` -> `2020.09.1` or if it was a
    bug-fix release: `2020.09.1` -> `2020.09.2`.
    Push to the official repo:
    ```
    $ git commit -a -m "Back to development"
    $ git push origin master
    ```
