# Building with Windows

This tutorial describes how to build [GStreamer Editing
Services](GES.md) using cerbero a freshly installed Windows 8.1 x86\_64.

# Download Software

## git

Install [git for Windows](http://msysgit.github.io/).

-   Bash only is fine
-   IMPORTANT: Select the install option “Checkout as-is, Commit as-is”

## Python 2.7

Install [Python 2.7.8](https://www.python.org/download/releases/2.7.8/)

-   Choose the MSI Installer for x86\_64.
-   For all users
-   To C:\\Python27\\

## MinGW

Install
[mingw-get](http://sourceforge.net/projects/mingw/files/Installer/)

-   To C:\\MinGW
-   Select the following packages in “Basic Setup”:
    -   mingw32-base
    -   mingw32-gcc-g++
    -   msys-base
-   Installation =&gt; Apply changes
-   Close the dialoge when complete

## CMake

Download the [CMake win32
installer](http://www.cmake.org/cmake/resources/software.html), since
there is no 64bit build.

You do not need to add CMake to the system path, since we are not using
CMD anyway.

## Text Editor

Make sure you have a decent text editor. I recommend Sublime or
Notepad++.

# Setup the shell

## Link on Desktop

Sadly I do not know how to make a .bat available in the task bar / dock,
so make a link on the Desktop.

-   Make a link on your Desktop to C:\\MinGW\\msys\\1.0\\msys.bat
-   Rename it to msys Shell and give it a nice icon.

## Edit fstab

This needs to be configured to be able to use the package manager
mingw-get.

-   Go to C:\\MinGW\\msys\\1.0\\etc\\
-   rename fastab.sample to fstab. If you installed MinGW to another
    folder, you need to edit this file.

## Install MinTTY

-   Open the shell from your Desktop.
-   It is a cmd like shell. Pasting sucks. We should install a cooler
    one with transparency and stuff.

`$ mingw-get install mintty`

Now we need to set it as the default shell

Add following line to C:\\MinGW\\msys\\1.0\\mys.bat after line 58:

`set MSYSCON=mintty.exe`

-   Open your new cool shell mintty.

It its scaled dynamically. You can copy with just selecting text. You
can paste with middle click. Cool.

## Editing your bash profile

We will need to add everything to our path manually.

Add the following lines at the end of C:\\MinGW\\msys\\1.0\\etc\\profile

`export PATH=$PATH:/c/Python27`\
`export PATH=$PATH:/c/Program\ Files\ `$x86$`/Git/bin`\
`export PATH=$PATH:/home/bmonkey/cerbero/`\
`export PATH=$PATH:/c/Program\ Files\ `$x86$`/CMake/bin`

`alias cerbero=cerbero-uninstalled`

Note that the cerbero path is the path where we will clone cerbero into
in the next step. You need to change it to your user name.

Save the file and restart your shell.

## Setting up git config

The bootstrap will fail if git config is not set up. Do the following:

`$ git config --global user.email you@example.com`
`$ git config --global user.name `“`Your`` ``Name`”

# Compile

### Checkout cerbero

`$ git clone git@gitlab.freedesktop.org:gstreamer/cerbero.git`

## Install dependencies

Now we need to get some extra dependencies from mingw-get to start the
bootstrap.

`$ mingw-get.exe install msys-perl msys-patch msys-bison msys-flex msys-coreutils`

## Bootstrap

Now we can start cerbero bootstrap.

If you cannot access the cerbero command, make sure its in the PATH in
your bash profile.

`$ cerbero bootstrap`

Go get some coffee.

## Building GStreamer Editing Services

`$ cerbero build gst-editing-services-1.0`

Go plant a tree. This can take hours.

## Building GStreamer Plugins

Since GES does not depend on all plugins, you need to build them
manually.

`$ cerbero build gst-plugins-bad-1.0`\
`$ cerbero build gst-plugins-ugly-1.0`\
`$ cerbero build gst-libav-1.0`

### Adding GStreamer tools to the PATH

You probably want to use ges-launch-1.0.exe and friends in the shell. To
do this, add the dist folder to the PATH.

In your bash profle:

`export PATH=$PATH:/home/bmonkey/cerbero/dist/windows_x86_64/bin/`

## Troubleshooting

### Configure hangs

If you encounter the configure process to freeze, you need to close the
shell and kill all sh.exe processes in the task manager. Alternatively
you can log out and log in.

`checking for msgfmt... /c/Users/Lubosz/cerbero/build-tools/bin/msgfmt`\
`checking for gmsgfmt... /c/Users/Lubosz/cerbero/build-tools/bin/msgfmt`\
`checking for xgettext... /c/Users/Lubosz/cerbero/build-tools/bin/xgettext`\
`checking for msgmerge...`
