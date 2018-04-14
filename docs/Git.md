---
short-description: Specifics of using Git in Pitivi
...

# Using Git in Pitivi

[Git](http://git-scm.com) is the most popular [distributed revision
control
system](http://en.wikipedia.org/wiki/Distributed_revision_control). Git
allows you to get a checkout (with full history) of the Pitivi code, as
a local git repository, and push your changes to a remote repository of
your own, to make them available for others.

In this page, we cover **specifics of how we use Git in the Pitivi
project**. For an introduction to Git, see the [official Git
tutorial/documentation page](http://git-scm.com/documentation) and [git
ready](http://gitready.com).


## Sending changes around

As can be seen in the [development workflow](Development_workflow.md),
best is to create an account on the GNOME GitLab instance and fork
[Pitivi](https://gitlab.gnome.org/GNOME/pitivi) there to create
your own remote `pitivi` repository. When you push branches to this
remote repository, you have the option to create a merge request.
A GitLab merge request is the same things as a GitHub pull request.
This way, the maintainers and other interested parties are notified
and can review the changes.


## When to use git pull

With rare exceptions, in Pitivi we rebase contributed commits before
pushing them to origin/master, to avoid merge commits. This worked fine
and it enforces some discipline, so there is no plan to change it.

When working on a issue, assuming you're following the [development
workflow](Development_workflow.md), you should have a specific branch.
To get the latest changes in your branch, normally in Pitivi you should
do something like `git fetch` and `git rebase origin/master`.

It should be safe to use `git pull` on the master branch, if you don't
work on it. Just make sure it's exactly what origin/master is and no
merge commit is created.


## Not going insane

It's much easier to understand what's the status of a git branch by
using a graphical tool such as `gitk` or
[gitg](https://wiki.gnome.org/Apps/Gitg) (tailored for GNOME, with a
really nice interface).

[Meld](http://meldmerge.org) can be very useful for reviewing a large
change to be committed. Simply run `meld .` in your local repository.

Set up your prompt to show the current branch info, and make sure
tab-completion works.
