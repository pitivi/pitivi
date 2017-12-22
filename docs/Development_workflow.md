---
short-description: How we do it
...

# Development Workflow

We use [Phabricator
tasks](https://phabricator.freedesktop.org/tag/pitivi/) to track all
bugs and feature requests. Feel free to open a task if you have found a
bug or wish to see a feature implemented. If it already exists,
subscribe to it to keep yourself updated with its progress. You can also
subscribe to the entire project.

## Picking a task to work on

To get involved, you can start with tasks tagged [Pitivi tasks for
newcomers](https://phabricator.freedesktop.org/tag/pitivi_tasks_for_newcomers/).
It's best to get in touch with us on our IRC channel `#pitivi` on
Freenode, to see if it's still meaningful.

Once you decide, assign the task to yourself in Phabricator.


## Fixing the task

Next is the fun part where you implement your cool feature, or fix an
annoying bug:


### Create a new git branch

Create a new branch with a relevant name in your local git repository.
The name must start with the task ID.

For example, if you're
going to work on task [T7674](https://phabricator.freedesktop.org/T7674)
titled "Traceback when selecting a JPG file in the import dialog", the
branch could be called T7674-import-img:

```
$ git checkout -b T7674-import-img origin/master
```


### Commit your changes

Once you have made your changes, commit them in your local git
repository. Follow the [GNOME
guidelines](https://wiki.gnome.org/Newcomers/CodeContributionWorkflow#Commit_guidelines)
for creating commits.

Be aware that when you create a commit, `pre-commit` is executed to
perform checks on the changes. In some cases it does some automatic
fixes – when this happens, make sure those are included in the commit you
want to create.


### Upload your commit to Phabricator

Now you're all set to push your first diff to
[Phabricator](https://phabricator.freedesktop.org/tag/pitivi) for review!

```
(ptv-flatpak) $ git-phab attach
```

If there is no tracking information for the current branch,
[git-phab](https://phabricator.freedesktop.org/diffusion/GITPHAB/repository/master/)
will complain, as it won't be able to figure out what your changes are.
You can specify the tracked branch like this:

```
$ git branch --set-upstream-to=origin/master
```

Attaching does many things:

- Creates multiple Differential Revisions representing each of your
unattached commits and updates the ones already attached. See for
example [D1617](https://phabricator.freedesktop.org/D1617).

- Amends the message of the previously-unattached commits so they
contain the associated Differential Revision URL. See for example
[b6a1384dbeef](https://phabricator.freedesktop.org/rPTVb6a1384dbeefe228158ad5aaf96fb53f6a7fffa9).

- Finds out the Task ID from the branch name.

- Attaches the Differential Revisions to the Task.

- Pushes your branch to a "staging" git repo, so we can try exactly what
you did.

We'll get an automatic email and then review it ASAP.

For those of you familiar with Phabricator's tool for managing
revisions, pay attention `arc` creates a single revision for the entire
branch, while our `git-phab` attaches each commit in the branch as a
separate revision.


## Using a custom staging repository

Optionally, you can set git-phab to push your branches to a personal
remote repository when you attach:

1. Add your cloned remote Pitivi repository as a remote to your local repository:

    ```
    $ git remote add github https://github.com/NICK/pitivi.git
    $ git remote set-url github https://github.com/NICK/pitivi.git
    $ git remote set-url --push github git@github.com:NICK/pitivi.git
    $ git remote show github | grep URL
      Fetch URL: https://github.com/NICK/pitivi.git
      Push  URL: git@github.com:NICK/pitivi.git
    ```
2. Set git-phab remote to your cloned remote Pitivi repository:

    ```
    $ git config phab.remote github
    ```
