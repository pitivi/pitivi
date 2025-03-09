---
short-description: How to update the sandbox used by the Pitivi development environment
...

# Updating the sandbox

We use the same [Flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json)
for both the [development environment](HACKING.md) sandbox and for the [nightly
build snapshot](Install_with_flatpak.md).

To have the CI run the tests as fast as possible, we use a Docker image with
all the sandbox dependencies cached. This image needs to be updated whenever
we want to update the manifest, otherwise the CI fails since it can't download
the latest dependencies.

## Update the flatpak runtime

To update the flatpak runtime version, look in `org.pitivi.Pitivi.json` for the
current version:

```
    "runtime-version": "43",
```

Check out what is the latest flatpak runtime version. For example:

```
$ flatpak remote-ls flathub --system | grep org.gnome.Platform
GNOME Application Platform version 3.38 org.gnome.Platform              3.38
GNOME Application Platform version 46   org.gnome.Platform              46
GNOME Application Platform version 47   org.gnome.Platform              47
```

Download the latest:

```
$ flatpak install org.gnome.Sdk/x86_64/47
```

Check out in the git history how we updated the runtime version in the past and
repeat with the latest SDK.


## Update the sandbox dependencies

Some of them can be updated automatically with
[flatpak-external-data-checker](https://github.com/flathub/flatpak-external-data-checker):

```
$ flatpak run --filesystem=$HOME/dev/pitivi/pitivi org.flathub.flatpak-external-data-checker build/flatpak/org.pitivi.Pitivi.json --update --edit-only
```

Create a commit with the automatically changed deps.

```
$ git commit -a -m "build: Update deps with flatpak-external-data-checker"
```

Other deps have to be checked and updated manually.

## Check the Python version

Check the Python version in the sandbox. For example, last time it was:

```
$ flatpak run --user --command=bash --devel org.gnome.Sdk/x86_64/47
[📦 org.gnome.Sdk ~]$ python --version
Python 3.12.9
```

When the Python version changes, update the `/app/lib/python3.12` occurrences
in the [flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json)
and also update the [Python dependencies](Updating_Python_dependencies.md).

When updating pylint, make a separate commit to fix the issues it complains
about:

```
(ptv-flatpak) $ ptvenv pre-commit run -a pylint
```

## Sync with flathub

Check if any changes to the [flathub Pitivi
manifest](https://github.com/flathub/org.pitivi.Pitivi) need to be ported over.

In particular, pay attention to the `shared-modules` git submodule to copy
`libcanberra` into `build/flatpak`.

## Rebuild your local dev env

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv --update
```

Run the tests:

```
(ptv-flatpak) $ ptvtests
```

If all goes well, push the branch to origin to be able to initiate the
generation of the CI image.

```
$ git checkout -b sdk
$ git push origin sdk
```


## Build the CI image

The "Build docker image for the CI" [GitLab
Schedule](https://gitlab.gnome.org/GNOME/pitivi/-/pipeline_schedules) rebuilds
every 24h the image we use for running the unittests. This image caches
the build of dependencies described in our Flatpak manifest.

Since it's using the "master" branch, you have to create a new schedule and
select the branch you just pushed ("sdk"). Leave Active unchecked.

Go back to the Schedules page and click the Play button of the schedule you just
created to start a pipeline. Notice in the Last Pipeline column a link to the
pipeline you just started.

After the pipeline succeeds, create a regular MR with your manifest changes and
notice the CI is green. If you fail to merge the MR, the "Build docker image for
the CI" will kick in later and recreate the image according to the manifest on
branch "master".
