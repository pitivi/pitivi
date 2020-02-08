# Testing

We have three sets of tests:
 - the normal unit tests (ninja test)
 - integration tests using GstValidate.
 - [manual tests](QA_Scenarios.md)

Since version [0.91](releases/0.91.md), our backend test suite is much
smaller and simpler; since most of the core functionality is now handled
by [GES](GES.md), you need to run GES's test suite instead if
you want to test more thoroughly.

## Unit tests

You can run the tests with the `ptvtests` alias created when you enter
the [development environment](HACKING.md):

```
$ alias ptvtests
ptvtests='ptvenv gst-validate-launcher /.../pitivi-dev/pitivi/tests/ptv_testsuite.py'
```

NOTE: If you are on [macOS or Windows](crossplatform.md), replace
`ptvtests` with `gst-validate-launcher tests/ptv_testsuite.py`.

Run the entire unit tests suite:

```
$ ptvtests
```

Run only the tests in a particular file:

```
$ ptvtests -t test_project
```

Run only one particular unit test:

```
$ ptvtests -t tests.test_project.TestProjectManager.test_loading_missing_project_file
```

Normally it should work to use just the name of the test method:

```
$ ptvtests -t test_loading_missing_project_file
```

To lists all the available tests, run:

```
$ ptvtests -L
```

### Writing unit tests

As mock library we use [Mock](http://www.voidspace.org.uk/python/mock/),
as it's now integrated into
[Python3](http://docs.python.org/dev/library/unittest.mock) which we use
as of [0.94](releases/0.94.md).

We use the `unittest.mock` module extensively for writing unit tests for
the UI.

If you're curious about our unit tests, the best way to get to know them
is to write a few Pitivi unit tests and have us review them. Check out
[how to set up your dev env](HACKING.md) and come in our [IRC channel or
Matrix room](http://www.pitivi.org/?go=contact)!

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
