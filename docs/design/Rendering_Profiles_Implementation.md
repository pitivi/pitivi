# Rendering Profiles Implementation

This is a page to track all the **issues related to the general
redesign/refactoring of project “profiles”** (a.k.a. presets or
templates) and all the related user interfaces (Project settings dialog,
Rendering dialog, Startup wizard). There are **dozens of bug reports and
mockups** scattered in the bug tracker. This page is an attempt to bring
those into a **cohesive whole**.

See **[tracker bug
630751](https://bugzilla.gnome.org/show_bug.cgi?id=630751)** for the
meta-bug that tracks all the other bugs related to this.

# Current overall status

-   emdash's rework of project settings and rendering has been merged as
    of december 2010:
    <http://jeff.ecchi.ca/blog/2010/12/10/new-project-settings-and-rendering-ui/>
-   the “startup wizard” has also been implemented:
    <http://jeff.ecchi.ca/blog/2010/11/23/startup-assistant/>
-   Two-pass rendering is currently [not
    easy](https://bugzilla.gnome.org/show_bug.cgi?id=603070)

As such, this page is mostly obsolete.

# Project profiles (emdash's branch)

The goal is to allow [Rendering
Profiles](design/Rendering_Profiles.md), and allow the user to save
custom profiles.

Waiting for emdash to finish the job :)

## Project settings dialog

-   “Save as default” button ([bug
    622079](https://bugzilla.gnome.org/show_bug.cgi?id=622079)):
    obsolete/useless, we should implement a “Last used settings” profile
    instead, selected by default.

Should allow/calculate any framerates [bug
584048](https://bugzilla.gnome.org/show_bug.cgi?id=584048)

-   also affects render dialog
-   already implemented in emdash's branch?

Do not block settings when applying a template [bug
580167](https://bugzilla.gnome.org/show_bug.cgi?id=580167)

-   already obsoleted in emdash's branch?

### Mockups

by Andreas Nilsson (in bug
[615337](https://bugzilla.gnome.org/show_bug.cgi?id=615337)

![](Project-settings-mockup-andreas.png "Project-settings-mockup-andreas.png")

by nekohayo:

![](Project-settings-mockup-nekohayo-2010-04.png "Project-settings-mockup-nekohayo-2010-04.png")

Note: the selected preset must default to “Last settings”, except if the
last settings were == one of the presets.

### Current implementation

Old and needs work:

![](Project-settings-emdash-2010-04.png "Project-settings-emdash-2010-04.png")

## Rendering dialog

Should basically be a clone of the project settings dialog with a couple
of additional options.

### Current implementation

Needs work:
![](Render-project-emdash-2010-04.png "fig:Render-project-emdash-2010-04.png")

# Startup wizard

![](Startup_wizard.png "Startup_wizard.png")

-   Implement the first part (the start wizard itself; see the
    screenshot above and [bug
    615570](https://bugzilla.gnome.org/show_bug.cgi?id=615570))
-   When clicking “Create new project...”, simply call the **new**
    “Project settings” window (see mockup above). That dialog defaults
    its preset to the “Last used settings” project preset/profile, this
    way the user doesn't have to do more than 2 clicks.
    -   If the user cancels out that window, come back to the startup
        wizard,
    -   If the user OKs that window, then we're done.
