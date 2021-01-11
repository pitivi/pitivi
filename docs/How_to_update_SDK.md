---
short-description: How to update the SDK used by the Pitivi development environment
...

# Updating the SDK

We use the same [Flatpak
manifest](https://gitlab.gnome.org/GNOME/pitivi/blob/master/build/flatpak/org.pitivi.Pitivi.json)
for both the [development environment](HACKING.md) sandbox and for the [official
build](Install_with_flatpak.md).

The Flatpak manifest is based on the `org.gnome.Platform` runtime which needs to
be updated as soon as possible after new GNOME releases take place.

The complexity in updating the runtime comes from the fact that we use our own
Docker image for running the tests and this needs to be updated also.

## Update your dev env locally

First, look in `org.pitivi.Pitivi.json` for the current version:

```
    "runtime-version": "3.38",
```

Grep the entire repo for this runtime version and replace it with the next
version.

Rebuild your local dev env:

```
$ . bin/pitivi-env
(ptv-flatpak) $ ptvenv --update
```

Run the tests:

```
(ptv-flatpak) $ ptvtests
```

If all goes well, push the branch to origin!

```
$ git checkout -b sdk
$ git push origin sdk
```

## Build the tests runner image

If you go to Gitlab pitivi page > CI / CD >
[Schedules](https://gitlab.gnome.org/GNOME/pitivi/-/pipeline_schedules) you can
see a "Build docker image for the CI" schedule targetting branch "master". This
rebuilds every 24h the image we use for running the unittests. This image caches
the build of dependencies described in our Flatpak manifest.

To create an initial image for the new SDK, start with creating a new schedule.
Set description "build new image", select the branch you just pushed ("sdk"),
uncheck Active.

Go back to the Schedules page and click the Play button to start a pipeline.
Notice in the Last Pipeline column a link to the pipeline you just started. When
it succeeds, you should be able to create a regular MR with your branch to merge
it.
