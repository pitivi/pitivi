---
short-description: How we do it
...

# Development Workflow

We use [GitLab](https://gitlab.gnome.org/GNOME/pitivi/issues) to track
all bugs and feature requests. Most of the time, you assign an issue
to yourself, work on it until it's fixed, and then you close it.

Interested users can enable notifications for an existing issue to
get an email when it's updated. It's also possible to change your
"Notification settings" for
[pitivi](https://gitlab.gnome.org/GNOME/pitivi) from the default
"Global" to "Watch", to receive notifications for any activity in the
entire project.

## Picking an issue to work on

To get involved, start with issues tagged
[4. Newcomers](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers).
It's best to get in touch with us on our IRC channel `#pitivi` on
Freenode, to see if it's still meaningful.

Once you decide, assign the issue to yourself in GitLab.

## Fixing the issue

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

1. In the [GitLab UI](https://gitlab.gnome.org/GNOME/pitivi) press the "fork"
   button (*WARNING: Make sure to be authenticated otherwise the button won't be
   avalaible*)

2. Add the remote git repository you just forked as a remote to your local git repository:

    git remote add *yourgitlabusername* https://gitlab.gnome.org/yourgitlabusername/pitivi

3. Push your branch to your fork with:

    git push *yourgitlabusername*

4. Create merge request either by the link that shows in the command line after
   pushing or in the GitLab UI clicking "Create merge request" in your branch.

[Gitlab workflow for contribution]: https://gitlab.gnome.org/GNOME/pitivi/
[gitlab]: https://gitlab.gnome.org/GNOME/pitivi/
