#!/bin/bash -i
# Indentation = 4 spaces.
#
# This script sets up the environment to use and develop pitivi with an
# uninstalled git checkout of pitivi and GES.
#
# It will set up LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, PKG_CONFIG_PATH,
# to prefer the uninstalled versions but also contain the installed ones.
#
# You can change the MYPITIVI variable your preferred location, that either:
#  + contains your own build of pitivi, ges, gst-python, etc.
#
#  + an empty location where you have R+W access, so that the script
#    can set up everything for you (recommended).
MYPITIVI=$HOME/pitivi-git
# Change this variable to 'master' if you prefer to work with the master branch
# When using "master", this script will automatically "pull --rebase" modules.
GST_RELEASE_TAG="1.0.2"
# If you care about building the GStreamer/GES developer API documentation:
BUILD_DOCS=false
# Here are some dependencies for building GStreamer and GES. If they're missing,
# we'll fetch the git repositories at the given version tag and compile.
# If you set those variables to "master", it will grab the latest dev version
GLIB_RELEASE_TAG="2.34.0" # "gobject-introspection" needs glib > 2.32
PYGOBJECT_RELEASE_TAG="3.4.0"
GOBJECT_INTROSPECTION_RELEASE_TAG="GOBJECT_INTROSPECTION_1_34_0"
#
# Everything below this line shouldn't be edited!
#

# Avoid building glib if we can, because it is annoying to use the "memory"
# backend for gsettings (which happens when we compile glib for some reason)
if pkg-config glib-2.0 --atleast-version=2.34; then
    MODULES_CORE="gobject-introspection pygobject"
else
    MODULES_CORE="glib gobject-introspection pygobject"
fi
# Do NOT use the following two variables directly, use $MODULES instead
MODULES_ALL="gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly gst-plugins-bad gst-ffmpeg gnonlin gst-editing-services gst-python"
MODULES_MINIMAL="gnonlin gst-editing-services gst-python"
# The following decision has to be made before we've set any env variables,
# otherwise the script will detect our "gst uninstalled" and think it's the
# system-wide install.
if pkg-config --list-all |grep gstreamer-1.0 &>/dev/null; then
    MODULES=$MODULES_MINIMAL
else
    MODULES=$MODULES_ALL
fi

# base path under which dirs are installed
PITIVI=$MYPITIVI

# base path under which dirs are installed
PITIVI_PREFIX=$PITIVI/prefix

# set up a bunch of paths
export PATH="\
$PITIVI/gst-editing-services/tools:\
$PITIVI/pitivi/bin/:\
$PITIVI/gstreamer/tools:\
$PITIVI/gst-plugins-base/tools:\
$PITIVI_PREFIX/bin:\
$PATH"

# /some/path: makes the dynamic linker look in . too, so avoid this
LD_LIBRARY_PATH=$PITIVI_PREFIX/lib:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
DYLD_LIBRARY_PATH=$PITIVI_PREFIX/lib:${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}
GI_TYPELIB_PATH=$PITIVI_PREFIX/share/gir-1.0:${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}
export PKG_CONFIG_PATH="$PITIVI_PREFIX/lib/pkgconfig:$PITIVI/pygobject:$PKG_CONFIG_PATH"


if pkg-config --list-all |grep gstreamer-1.0 &>/dev/null; then
  echo "Using system-wide GStreamer 1.0"
else
  echo "Using a local build of GStreamer 1.0"
  # GStreamer ffmpeg libraries
  for path in libavformat libavutil libavcodec libpostproc libavdevice
  do
     LD_LIBRARY_PATH=$PITIVI/gst-ffmpeg/gst-libs/ext/ffmpeg/$path:$LD_LIBRARY_PATH
     DYLD_LIBRARY_PATH=$PITIVI/gst-ffmpeg/gst-libs/ext/ffmpeg/$path:$DYLD_LIBRARY_PATH
  done

  # GStreamer plugins base libraries
  for path in app audio cdda fft interfaces pbutils netbuffer riff rtp rtsp sdp tag utils video
  do
    LD_LIBRARY_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path/.libs:$LD_LIBRARY_PATH
    DYLD_LIBRARY_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
    GI_TYPELIB_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path:$GI_TYPELIB_PATH
  done

  # GStreamer plugins bad libraries
  for path in basecamerabinsrc codecparsers interfaces
  do
    LD_LIBRARY_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path/.libs:$LD_LIBRARY_PATH
    DYLD_LIBRARY_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
    GI_TYPELIB_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path:$GI_TYPELIB_PATH
  done

  # GStreamer core libraries
  for path in base net check controller
  do
    LD_LIBRARY_PATH=$PITIVI/gstreamer/libs/gst/$path/.libs:$LD_LIBRARY_PATH
    DYLD_LIBRARY_PATH=$PITIVI/gstreamer/libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
    GI_TYPELIB_PATH=$PITIVI/gstreamer/libs/gst/$path:$GI_TYPELIB_PATH
  done

  LD_LIBRARY_PATH=$PITIVI/gstreamer/gst/.libs:$LD_LIBRARY_PATH
  DYLD_LIBRARY_PATH=$PITIVI/gstreamer/gst/.libs:$DYLD_LIBRARY_PATH
  GI_TYPELIB_PATH=$PITIVI/gstreamer/gst:$GI_TYPELIB_PATH

export PKG_CONFIG_PATH="$PITIVI/gstreamer/pkgconfig\
:$PITIVI/gst-plugins-base/pkgconfig\
:$PITIVI/gst-plugins-good/pkgconfig\
:$PITIVI/gst-plugins-ugly/pkgconfig\
:$PITIVI/gst-plugins-bad/pkgconfig\
:$PITIVI/gst-ffmpeg/pkgconfig\
:${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"

export GST_PLUGIN_PATH="\
$PITIVI/gstreamer/plugins\
:$PITIVI/gst-plugins-base/ext\
:$PITIVI/gst-plugins-base/gst\
:$PITIVI/gst-plugins-base/sys\
:$PITIVI/gst-plugins-good/ext\
:$PITIVI/gst-plugins-good/gst\
:$PITIVI/gst-plugins-good/sys\
:$PITIVI/gst-plugins-ugly/ext\
:$PITIVI/gst-plugins-ugly/gst\
:$PITIVI/gst-plugins-ugly/sys\
:$PITIVI/gst-plugins-bad/ext\
:$PITIVI/gst-plugins-bad/gst\
:$PITIVI/gst-plugins-bad/sys\
:$PITIVI/gst-ffmpeg/ext/\
:$PITIVI/gst-openmax/omx/.libs\
:$PITIVI/gst-omx/omx/.libs\
:$PITIVI/gst-plugins-gl/gst/.libs\
:$PITIVI/clutter-gst/clutter-gst/.libs\
:$PITIVI/plugins\
:$PITIVI/farsight2/gst\
:$PITIVI/farsight2/transmitters\
:$PITIVI/libnice/gst\
:${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"

  # don't use any system-installed plug-ins at all
  export GST_PLUGIN_SYSTEM_PATH=
  # set our registry somewhere else so we don't mess up the registry generated
  # by an installed copy
  export GST_REGISTRY=$PITIVI/gstreamer/registry.dat
  # Point at the uninstalled plugin scanner
  export GST_PLUGIN_SCANNER=$PITIVI/gstreamer/libs/gst/helpers/gst-plugin-scanner

  # once MANPATH is set, it needs at least an "empty"component to keep pulling
  # in the system-configured man paths from man.config
  # this still doesn't make it work for the uninstalled case, since man goes
  # look for a man directory "nearby" instead of the directory I'm telling it to
  export MANPATH=$PITIVI/gstreamer/tools:$PITIVI_PREFIX/share/man:$MANPATH
  pythonver=`python -c "import sys; print sys.version[:3]"`
fi

# And anyway add GStreamer editing services library
export LD_LIBRARY_PATH=$PITIVI/gst-editing-services/ges/.libs:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$PITIVI/gst-editing-services/ges/.libs:$DYLD_LIBRARY_PATH
export PATH=$PITIVI/gst-editing-services/tools:$PATH
GI_TYPELIB_PATH=$PITIVI/gst-editing-services/ges:$GI_TYPELIB_PATH
GI_TYPELIB_PATH=$PITIVI_PREFIX/share/gir-1.0${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}:/usr/lib64/girepository-1.0:/usr/lib/girepository-1.0

# And GNonLin
export GST_PLUGIN_PATH=$GST_PLUGIN_PATH:$PITIVI/gnonlin/gnl/.libs

# And python
PYTHONPATH=$MYPITIVI/pygobject:$MYPITIVI/gst-python${PYTHONPATH:+:$PYTHONPATH}
export LD_LIBRARY_PATH=$PITIVI/pygobject/gi/.libs:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$PITIVI/pygobject/gi/.libs:$DYLD_LIBRARY_PATH

export LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH
export GI_TYPELIB_PATH
export PYTHONPATH


# Force build to happen automatically if the folders are missing
# or if the --build parameter is used:
ready_to_run=0

if test ! -d $PITIVI; then
    echo "===================================================================="
    echo "Creating initial set of folders in $PITIVI"
    echo "===================================================================="

    echo "New $PITIVI directory"
    mkdir $PITIVI/
    if [ $? -ne 0 ]; then
        exit 1
    fi
    echo "New $PITIVI_PREFIX directory"
    mkdir $PITIVI_PREFIX
    if [ $? -ne 0 ]; then
        exit 1
    fi
elif [ "$1" != "--build" ]; then
    # The folders existed, and the user just wants to set the shell environment
    ready_to_run=1
fi


if [ "$ready_to_run" != "1" ]; then
    cd $PITIVI
    for m in $MODULES_CORE
    do
        echo ""
        echo "Building $m"
        # If the folder doesn't exist, check out the module. Later on, we will
        # update it anyway.
        if test ! -d $m; then
            git clone git://git.gnome.org/$m
            if [ $? -ne 0 ]; then
                echo "Could not download the code for $m ; result: $?"
                exit 1
            fi
        fi
        cd $m
        # Take into account whether the user want stable releases or "master"
        if [ $m == "glib" ]; then
            # Silly hack for the fact that glib changes the "mkinstalldirs" file
            # when compiling, which prevents git pull --rebase from working
            git checkout -- mkinstalldirs
            git checkout $GLIB_RELEASE_TAG
            if [ $GLIB_RELEASE_TAG == "master" ]; then
                git pull --rebase
                if [ $? -ne 0 ]; then
                    exit 1
                fi
            fi
        elif [ $m == "gobject-introspection" ]; then
            git checkout $GOBJECT_INTROSPECTION_RELEASE_TAG
            if [ $GOBJECT_INTROSPECTION_RELEASE_TAG == "master" ]; then
                git pull --rebase
                if [ $? -ne 0 ]; then
                    exit 1
                fi
            fi
        elif [ $m == "pygobject" ]; then
            git checkout $PYGOBJECT_RELEASE_TAG
            if [ $PYGOBJECT_RELEASE_TAG == "master" ]; then
                git pull --rebase
                if [ $? -ne 0 ]; then
                    exit 1
                fi
            fi
        else
            git pull --rebase
            if [ $? -ne 0 ]; then
                exit 1
            fi
        fi


        # Now compile that module
        ./autogen.sh --prefix=$PITIVI/prefix --disable-gtk-doc
        if [ $? -ne 0 ]; then
            echo "Could not run autogen for $m ; result: $?"
            exit 1
        fi

        make
        if [ $? -ne 0 ]; then
            echo "Could not run make for $m ; result: $?"
            exit 1
        fi

        if [ "$m" != "pygobject" ]; then
            make install
            if [ $? -ne 0 ]; then
                echo "Could not install $m ; result: $?"
                exit 1
            fi
        fi

        cd ..
    done



    # Build all the necessary gstreamer modules.
    for m in $MODULES
    do
        echo ""
        echo "Building $m"
        # If the folder doesn't exist, check out the module. Later on, we will
        # update it anyway.
        if test ! -d $m; then
            git clone git://anongit.freedesktop.org/gstreamer/$m
            if [ $? -ne 0 ]; then
                echo "Could not checkout $m ; result: $?"
                exit 1
            fi
        fi

        cd $m
        git remote update  # In case you haven't got the latest release tags...
        git checkout $GST_RELEASE_TAG
        if [ $? -ne 0 ]; then
            echo "Could not run checkout $GST_RELEASE_TAG for $m ; result: $?"
            echo 'Trying "master" instead...'
            git checkout master && git pull --rebase
            if [ $? -ne 0 ]; then
                echo "Checkout and rebase failed, aborting"
                exit 1
            fi
        fi
        # Silly hack for the fact that the version-controlled po/ files are
        # changed during compilation of the "gstreamer" module, which prevents
        # git pull --rebase from working
        if [ $m == "gstreamer" ]; then
            git checkout -- po
        fi
        if [ $GST_RELEASE_TAG == "master" ]; then
            git pull --rebase
            if [ $? -ne 0 ]; then
                exit 1
            fi
        fi

        if $BUILD_DOCS; then
            ./autogen.sh
        else
            ./autogen.sh --disable-gtk-doc
        fi
        if [ $? -ne 0 ]; then
            echo "Could not run autogen for $m ; result: $?"
            exit 1
        fi

        make
        if [ $? -ne 0 ]; then
            echo "Could not compile $m ; result: $?"
            exit 1
        fi
        cd ..
    done

    # And obviously ... PiTiVi itself
    if test ! -d $PITIVI/pitivi; then
        git clone git://git.gnome.org/pitivi
    fi
    cd pitivi
    ./autogen.sh
    if [ $? -ne 0 ]; then
        echo "Could not run autogen for Pitivi ; result: $?"
        exit 1
    fi
    make
    ready_to_run=1
    echo "===================================================================="
    echo "                   BATTLECRUISER OPERATIONAL                        "
    echo "                          >(°)__/                                   "
    echo "                           (_~_/                                    "
    echo "                         ~~~~~~~~~~~~                               "
    echo "===================================================================="
fi



if [ $ready_to_run == 1 ]; then
    cd $PITIVI/pitivi
    # Change the looks of the prompt, to help us remember we're in a subshell.
    # If the user has some custom git bash helpers, try preserving them.

    function function_exists {
        FUNCTION_NAME=$1
        [ -z "$FUNCTION_NAME" ] && return 1
        declare -F "$FUNCTION_NAME" > /dev/null 2>&1
        return $?
        }
    if function_exists __git_ps1
    then
        # Display "PTV env:", path, the output of __git_ps1, " $ "
        changed_PS1='PS1="\[$(tput bold)$(tput setb 1)$(tput setaf 7)\]PTV env:\w\[$(tput sgr0)\]\$(__git_ps1)$ "'
    else
        # Display "PTV env:", path, " $ "
        changed_PS1='PS1="\[$(tput bold)$(tput setb 1)$(tput setaf 7)\]PTV env:\w\[$(tput sgr0)\] $ "'
    fi
    bash --rcfile <(cat ~/.bashrc; echo $changed_PS1)
fi
