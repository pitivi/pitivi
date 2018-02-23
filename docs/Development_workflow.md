---
short-description: How we do it
...

# Development Workflow

We use [Gitlab](https://gitlab.gnome.org/GNOME/pitivi/issues) to track all
bugs and feature requests. Feel free to open a task if you have found a
bug or wish to see a feature implemented. If it already exists,
subscribe to it to keep yourself updated with its progress. You can also
subscribe to the entire project.

## Picking a task to work on

To get involved, you can start with tasks tagged [Pitivi tasks for
newcomers](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers).
It's best to get in touch with us on our IRC channel `#pitivi` on
Freenode, to see if it's still meaningful.

Once you decide, assign the task to yourself in gitlab.

## Fixing the task

Next is the fun part where you implement your cool feature, or fix an
annoying bug:


### Create a new git branch

Create a new branch with a relevant name in your local git repository.

```
$ git checkout -b feature_name origin/master
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

### Propose your patches

1. In the [GitLab UI](https://gitlab.gnome.org/GNOME/pitivi) press the "fork
   button (*WARNING: Make sure to be connected otherwise the button won't be
   avalaible*)

2. Add your remote to you repository:

    git remote add *yourgitlabusername* https://gitlab.gnome.org/yourgitlabusername/pitivi `

3. Push your branch to your fork with:

    git push *yourgitlabusername*

4. Create merge request either by the link that shows in the command line after
   pushing or in the GitLab UI clicking "Create merge request" in your branch.

[Gitlab workflow for contribution]: https://gitlab.gnome.org/GNOME/pitivi/
[gitlab]: https://gitlab.gnome.org/GNOME/pitivi/