---
short-description: How we do it
...

# Development Workflow

We use [GitLab](https://gitlab.gnome.org/GNOME/pitivi/issues) to track
all bugs and feature requests. Most of the time, you announce you are
working on an issue, work on it until it's fixed, and then the issue is
closed automatically when a commit with "Fixes #issue_number" is merged.

Interested users can enable notifications for an existing issue to
get an email when it's updated. It's also possible to change your
"Notification settings" for
[pitivi](https://gitlab.gnome.org/GNOME/pitivi) from the default
"Global" to "Watch", to receive notifications for any activity in the
entire project.

## Picking an issue to work on

To get involved, start with issues tagged
[4. Newcomers](https://gitlab.gnome.org/GNOME/pitivi/issues?label_name%5B%5D=4.+Newcomers).
It's best to get in touch with us in our [chat
room](https://www.pitivi.org/contact/), to see if it's still meaningful, etc.

Once you decide, add a comment on the issue saying you're working on it.

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
fixes – when this happens, make sure those are included in the commit
you want to create.

### Propose your patches

Patches are proposed by creating a merge request in GitLab.

To do this, you need your own Pitivi repo on [GNOME's
GitLab](https://gitlab.gnome.org). Start by creating an account. Then go
to
[gitlab.gnome.org/GNOME/pitivi](https://gitlab.gnome.org/GNOME/pitivi)
and press the "fork" button. *Make sure to be authenticated otherwise
the button won't be available.*

To be able to push seamlessly to your remote fork, [add your public ssh
key to GitLab](https://gitlab.gnome.org/profile/keys).

Add the remote git repository you just forked as a "remote" to your
local git repository:

```
$ git remote add your_gitlab_username git@gitlab.gnome.org:your_gitlab_username/pitivi.git
$ git fetch your_gitlab_username
```

To make a merge request, first push your branch to your fork:

```
$ git push your_gitlab_username your_branch_name
[...]
remote:
remote: To create a merge request for docs, visit:
remote:   https://gitlab.gnome.org/your_gitlab_username/pitivi/merge_requests/new?merge_request%5Bsource_branch%5D=your_branch_name
remote:
[...]
```

Open the displayed URL in the browser and fill the form for creating a
merge request. Alternatively, go to
[gitlab.gnome.org/GNOME/pitivi](https://gitlab.gnome.org/GNOME/pitivi)
&gt; Merge Requests &gt; New merge request.

> Note: Make sure to select "Allow commits from members who can merge to
the target branch". This way we'll be able to rebase the branch easily
to be able to merge it in case it's behind origin/master.

### The code review cycle

One of the maintainers will review your changes and either merge your
branch, or comment and ask for changes.

The comments made by the reviewer have to be addressed by you:

- If you disagree with a comment, reply how it's better differently.

- If you agree with the requests for changes, implement the changes,
commit them and push your branch.

Mark the addressed comment threads as "resolved", unless there is a
disagreement. Finally, inform the reviewer when you are done!

Everybody can see the merge request and comment on it. If you see an
interesting merge request, feel free to review it yourself.

#### Tips for creating the commits

Run `gitk main_file_you_changed.py` to see how the commit messages
are formatted and try to follow the model.

Before pushing, use `gitk` to have a quick look at your branch and
review your own changes.

Avoid creating separate "update" commits. We don't need the full history
of changes in the commit history. Consider squashing these in one of the
previous commits where it makes sense.

If you add some new logic and a unittest for it, the unittest should be
included in the same commit as the tested logic.
