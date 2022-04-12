# Testing

We have three sets of tests:
 - the normal unit tests
 - integration tests
 - [manual tests](QA_Scenarios.md)

Since version [0.91](releases/0.91.md) the test suite is set up similarly to
the GStreamer tests, using GstValidate. The GES backend also has its own test
suite, preventing things falling apart.

## Unit tests

Run the entire unit tests suite:

```
$ ptvtests
```

Run only a set of tests by specifying `-t`. For example:

```
$ ptvtests -t test_project
$ ptvtests -t test_project.TestProjectManager
$ ptvtests -t test_project.TestProjectManager.test_loading_missing_project_file
$ ptvtests -t TestProjectManager
$ ptvtests -t test_loading_missing_project_file
$ ptvtests -t Only_the_tests_affecting_the_clips_widgets_please
```

To list the available tests, run:

```
$ ptvtests -L
```

NOTE: `ptvtests` is an alias created when you enter the [development
environment](HACKING.md). If you are on [macOS or Windows](crossplatform.md),
replace `ptvtests` with `gst-validate-launcher tests/ptv_testsuite.py`.

```
$ alias ptvtests
ptvtests='ptvenv gst-validate-launcher /.../pitivi-dev/pitivi/tests/ptv_testsuite.py --dump-on-failure'
```

### Writing unit tests

Start by reading the utility methods in `tests/common.py`.

The tests for the logic in a specific file have a corresponding tests file. For
example the tests for `pitivi/clip_properties/color.py` can be found in
`tests/test_clipproperties_color.py`. Note the undo/redo tests in
`tests/test_undo_*` cover the same area as others such as the timeline.

When writing a new test, look for similar ones to copy the initial part doing
the setup. Most probably you find a good example and learn something in the
process. We have a large number of tests covering most of the codebase.

We use the `unittest.mock` standard [Python
module](https://docs.python.org/3/library/unittest.mock.html) extensively in the
unit tests, especially for the UI.

Unit tests can be [debugged](Debugging.md#debugging-unit-tests) by setting the
`PITIVI_VSCODE_DEBUG` environment variable.

If you're curious about our unit tests, the best way to get to know them is to
write a few and have us review them. Check out [how to set up your dev
env](HACKING.md) and come in our [chat room](https://www.pitivi.org/contact/)!

## Integration tests

The integration tests are run with GstValidate. They are located in the
[tests/validate-tests](https://gitlab.gnome.org/GNOME/pitivi/tree/master/tests/validate-tests)
directory. Each `.scenario` file in the
[scenarios](https://gitlab.gnome.org/GNOME/pitivi/tree/master/tests/validate-tests/scenarios)
subdirectory contains a sequence of actions which represent a test.

When a test is run, the actions in the scenario are performed by
handlers in
[pitivi/utils/validate.py](https://gitlab.gnome.org/GNOME/pitivi/blob/master/pitivi/utils/validate.py),
or by handlers in GES. The handlers generally act on the widgets and
check the expected effect has been obtained on the GES objects. Besides
the checks integrated in the handlers, for now it is not possible to
have additional checks.

A scenario file is [created
automatically](http://developer.pitivi.org/Bug_reporting.html#sharing-sample-files-projects-and-scenarios)
each time Pitivi is used.

You can run the integration tests with:

```
$ ptvenv tests/validate-tests/runtests
```
