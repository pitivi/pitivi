---
short-description: How to update the Git pre-commit hooks which sanitize the code
...

# pre-commit hooks

When you enter the [development environment](HACKING.md), our `pre-commit.hook`
[script](https://gitlab.gnome.org/GNOME/pitivi/-/blob/master/pre-commit.hook) is
symlinked in your local git repository as `.git/hooks/pre-commit`, serving as
the [Git pre-commit
hook](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks).

When you make a git commit, the following happens:

- The `pre-commit.hook` script runs the (confusingly named) `pre-commit` tool
**in the flatpak sandbox**.

- The `pre-commit` tool runs the hooks configured in
[.pre-commit-config.yaml](https://gitlab.gnome.org/GNOME/pitivi/-/blob/master/.pre-commit-config.yaml)

Sooner or later you'll want to update the `pre-commit` framework and its hooks.

## How to update the `pre-commit` tool

The `pre-commit` tool is installed in the flatpak sandbox through
[python3-pre-commit.json](https://gitlab.gnome.org/GNOME/pitivi/-/blob/master/build/flatpak/python3-pre-commit.json).
The `python3-pre-commit.json` file is generated with `flatpak-pip-generator`.
See the instructions for [updating the Python
dependencies](Updating_Python_dependencies.md).

## How to update the hooks

The `.pre-commit-config.yaml` file contains the list of hooks we use, grouped by
the git repo in which they can be found. The repos are downloaded and cached by
the `pre-commit` tool on demand. These hooks are executed **each in their own
own virtualenv**.

A special case is the `local` repo which groups the hooks installed alongside
the pre-commit framework, in the sandbox. We only need the `pylint` hook to be
run **in the sandbox** instead of in its own virtualenv, such that it has access
to the Python environment in the sandbox.

To update `pylint`, follow the instructions for [updating the Python
dependencies](Updating_Python_dependencies.md).

To update the regular hooks, take the repos one by one, check what is the latest
version and update the entry in the `.pre-commit-config.yaml` file. After
updating each repo, validate the entire codebase and fix all the newfound
errors.

For example, suppose we just updated the
`https://github.com/pre-commit/pre-commit-hooks.git` repo to revision `v3.4.0`:

```
  - repo: https://github.com/pre-commit/pre-commit-hooks.git
    rev: v3.4.0
    hooks:
      - id: check-yaml
```

To run the `check-yaml` hook on the entire codebase:

```
(ptv-flatpak) $ ptvenv pre-commit run -a check-yaml
```

If you feel brave, you can use `pre-commit` itself to update the hooks:

```
(ptv-flatpak) $ ptvenv pre-commit autoupdate
```

At the end, do a final check by running all the hooks on the entire codebase:

```
(ptv-flatpak) $ ptvenv pre-commit run -a
```
