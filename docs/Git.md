# Git

[Git](http://git-scm.com) is the most popular [distributed revision
control
system](http://en.wikipedia.org/wiki/Distributed_revision_control) used
by the kernel, X, GStreamer, GNOME, etc... Git allows you to get a
checkout (with full history) of the Pitivi code, create your own
branches, publish those, etc... without the need for access to the
central repository.

Indeed, one of the very big strengths of a decentralized (a.k.a.
distributed) system is that it is truly open and meritocratic: it allows
you to do whatever changes you want to your repository, request
feedback/reviews and then request that others pull your changes into the
main repository on which others base their work upon. See
<http://youtube.com/watch?v=4XpnKHJAok8#t=18m05s> for an explanation of
this phenomenon.

This page is not meant to be a general tutorial for Git; for that, see
the [GNOME Git page](https://live.gnome.org/Git), the [official Git
tutorial/documentation page](http://git-scm.com/documentation) and [git
ready](http://gitready.com). In this page, we will cover some more
advanced usage and the **specifics of how we use Git in the Pitivi
project**. This is aimed at people coming from Bazaar or Subversion.

# First steps: checking out the main repository

`git clone `[`git://git.gnome.org/pitivi`](git://git.gnome.org/pitivi)`  # do the initial repository checkout`

You should now have a directory called pitivi with the latest version of
the files checked out. You are in the **`master`** branch.

**Note**: unlike in Bazaar or other DVCSes, in git you only do this
once; the “remotes” and branches in are all self-contained in the
repository. In other words, you only do one checkout and do everything
inside it using branches and remotes.

# Dealing with remotes and branches

You can see all local branches by using the `git branch` command. The
branch you are working in is marked with an asterisk (**\***). You can
view all branches, including the remote ones, by doing:

`git branch -a`

You'll notice that it shows you all the branches available from the
<http://git.gnome.org/pitivi> repository.

Let's say we add multiple people's remote repositories inside your local
repository (see [Git repositories](Git_repositories.md) for the
list of our known remotes):

`git remote add nekohayo `[`https://github.com/nekohayo/pitivi.git`](https://github.com/nekohayo/pitivi.git)\
`git remote add thiblahute `[`https://github.com/thiblahute/pitivi.git`](https://github.com/thiblahute/pitivi.git)

To update the remotes:

`git remote update`

And now you would be able to do stuff like:

`git checkout thiblahute/somebranch`

Or, to create a new local branch based on that branch:

`git checkout -b mynewbranch thiblahute/somebranch`

“git remote update” does not update your local branches, only the
remotes. For example, if you have a local branch called “titles” based
on “nekohayo/titles” (remote branch) and the “titles” branch on the
“nekohayo” remote changed, you will have to checkout your local “titles”
branch and update it to reflect the changes (with git pull --rebase, or
a git reset --hard, depending on whether or not you want to keep your
local changes).

When the remote party has deleted some branches, you're still left with
local copies of those remote branches... eventually you can clean it up
with:

`git remote prune REMOTE_NAME`

I like to think of “git checkout” like “svn switch”: it allows you to
move between branches (among other things). So, to go back to the main
branch, you do “git checkout master”.

## Creating a work branch

It is good practice never to do work on the master branch (more details
in the next section). Therefore you need to create a work branch :

` git branch work master`

If you use `git branch` you will now see your new branch... but you are
still in `master`.

To switch to your `work` branch you need to check it out using:

` git checkout work`

And it tells you it has successfully switched to the work branch.

**Tip**: you can branch and checkout in one step using the
`-b `<new_branch> option of `git checkout` Therefore the two steps above
become:

` git checkout -b work master`

## Pitivi-specific gotcha: don't use git pull

Typically, in Pitivi we use rebase and reset more often than “git merge”
when merging your changes. This means two things:

-   You should not do your work directly on your “master” branch. You
    should do it in separate branches instead, unless you really know
    what you're doing and can handle resolving conflicts. We recommend
    that you keep master (or whatever the main development base is)
    identical to the upstream (“origin”) remote branch.
-   To update your local master branch (or whatever your base is) when
    you're on the local branch, always use “git pull --rebase”.

Really, in the Pitivi context you don't want to use “git pull” (this
creates merge commits and becomes quite messy over time). However, the
general rules of thumb regarding rebasing are:

-   Branches on the official repository (git.gnome.org/pitivi) should
    only be fast-forward, because that's what contributors may base
    themselves upon
-   Individual contributors might use “git rebase -i” when they feel it
    necessary to sync up their work. Otherwise, we will do it at the
    time of the “merge” (so to speak). Rebasing is a more advanced
    notion, so refer to git ready and to this Pitivi-specific video
    tutorial: <http://youtube.com/watch?v=6WU4jKti_vo>

# Publishing your work / adding your own remote to push to

Several free git hosting services exist out there where you can create
very quickly some repositories and publish your branch there. These
websites will contain information on how to add your publishing remote
URL. Here's an example of how you can add your remote git repository
where you'll push your changes, with github (notice that I named the
remote “github” instead of “origin”, since origin is git.gnome.org):

`git remote add github git@github.com:my_user/pitivi.git`

Let's say you created a working branch locally (called `mytest`) and
that you named your remote repository `myremote`, and you want to
publish it so people can see what you have done, try it out, etc. The
first time you will have to tell git **where** you want to push that
branch:

` git push myremote mytest`

This will automatically:

-   Create a `mytest` branch on your remote repository
-   Copy over all the commits
-   Make git remember where that branch is stored remotely

The next time you want to push your work remotely, you just to be within
that branch and do:

` git push`

To delete a branch (or tag) on the remote repository:

`git push REMOTENAME :BRANCHNAME`

This command may look strange, but it is literally telling git *push,
onto REMOTENAME, “nothing” into BRANCHNAME*.

Once that's done, others will be able to do a “git remote prune” to see
those changes on their end.

# Not going insane

You are very quickly going to have a lot of branches. There are
graphical tools to view what you have locally and make some
changes/actions without needing to rely on the command line (unless you
prefer the command line interface). We recommend
[gitg](https://wiki.gnome.org/Apps/Gitg) (tailored for GNOME, with a
really nice interface), though there are others like giggle or gitk.

Other *very* useful tools are:

-   [Git Meld](https://github.com/wmanley/git-meld) (not needed anymore,
    simply put “meld = difftool --dir-diff -t meld” in the alias section
    of your \~/.gitconfig file)
-   [Showing the current branch name at all
    times](http://asemanfar.com/Current-Git-Branch-in-Bash-Prompt)
-   [Git autocompletion for
    Bash](http://gitready.com/advanced/2009/02/05/bash-auto-completion.html)

Nice Git features to learn about:

-   “git grep”
-   “git bisect” (for pinpointing regressions)
-   “git rebase -i” is an extremely powerful tool once you get used to
    it. See the various tutorials/documentation about it, this
    Pitivi-specific video tutorial:
    <http://youtube.com/watch?v=6WU4jKti_vo>
-   “git add -p” (or use the little “+” icons in
    [gitg](https://wiki.gnome.org/Apps/Gitg)'s commit mode) to
    stage/commit only portions of a file (allowing you to easily plan
    and split work across different commits)

## Tips and tricks/gotchas for Bazaar/Subversion users

-   To revert some files to the version provided by git, use “git
    checkout thefiles”, not “git revert”.
-   “git checkout” is also used for switching between branches (or to
    any particular commit/point in the history). It is somewhat similar
    to “svn switch”.
-   To create a branch, you do “git checkout -b my\_new\_local\_branch
    theremote/thesourcebranch”, not “git branch”.
-   To delete a branch, you do “git branch -D thebranch”.
-   To apply a patch without committing, use “git apply foo.diff”
-   To apply a patch and create commits at the same time, use “git am
    foo.patch”
-   In the Pitivi context, do not ever use “git pull” (unless you really
    know what you're doing). Use “git pull --rebase”, to get the
    equivalent of a “svn up”. If you have changes in the branch you're
    “pulling”, it will rebase them on top of it (but, as mentioned
    previously, you should not do your work directly on the master
    branch unless you know what you're doing and know how to resolve
    potential rebase conflicts).

Git's syntax can arguably be quite arcane. Take a look at the
\~/.gitconfig file: you can add an \[alias\] section to create command
aliases. This is nekohayo's gitconfig:

`[alias]`\
`   diffstat = diff --stat`\
`   staged = diff --cached`\
`   unstaged = diff`\
`   both = diff HEAD`\
`   oneline = log --pretty=oneline --abbrev-commit`

`   newbranch = checkout -b # destination source, not the other way around`\
`   deletebranch = branch -D`\
`   switch = checkout`\
`   uncommit = reset HEAD~1`\
`   nukefromorbit = clean -fxd # use with extreme caution.`\
`   up = pull --rebase`\
`   patch = am`

`   meld = difftool --dir-diff -t meld`
