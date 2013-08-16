#!/bin/bash -i
# Indentation = 4 spaces.
#
# This script sets up the environment to use and develop Pitivi.
#
# The git projects will be cloned in ~/pitivi-git, unless you specify
# a different directory, for example:
#     MYPITIVI=~/dev/pitivi pitivi-git-environment.sh
#
# LD_LIBRARY_PATH, DYLD_LIBRARY_PATH, PKG_CONFIG_PATH are set to
# prefer the cloned git projects and to also allow using the installed ones.

MYPITIVI=${MYPITIVI:-$HOME/pitivi-git}

# Change this variable to 'master' if you prefer to work with the master branch.
# When using "master", this script will automatically "pull --rebase" modules.
# For now, we are using master until we depend on a released version.
GST_RELEASE_TAG="master"

# If you care about building the GStreamer/GES developer API documentation:
BUILD_DOCS=false

# Here are some dependencies for building GStreamer and GES. If they're missing,
# we'll fetch the git repositories at the given version tag and compile.
# If you set those variables to "master", it will grab the latest dev version
GLIB_RELEASE_TAG="2.34.2" # "gobject-introspection" needs glib > 2.32
PYGOBJECT_RELEASE_TAG="3.8.0"
GOBJECT_INTROSPECTION_MINIMUM_VERSION="1.34.2"
GOBJECT_INTROSPECTION_RELEASE_TAG="GOBJECT_INTROSPECTION_$(echo $GOBJECT_INTROSPECTION_MINIMUM_VERSION | tr '.' '_')"


#
# Everything below this line shouldn't be edited!
#

if ! pkg-config glib-2.0 --atleast-version=$GLIB_RELEASE_TAG; then
    MODULE_GLIB="glib"
else
  echo "glib is up to date, using the version already available."
fi
if pkg-config gobject-introspection-1.0 --atleast-version=$GOBJECT_INTROSPECTION_MINIMUM_VERSION; then
  echo "gobject-introspection-1.0 is up to date, but we are using a local build because you might want to fix bugs if you find any."
fi
if python2 -c "import gi; gi.check_version('${PYGOBJECT_RELEASE_TAG}')" &> /dev/null; then
  echo "pygobject is up to date, but we are using a local build because you might want to fix bugs if you find any."
fi
MODULES_CORE="${MODULE_GLIB} gobject-introspection pygobject"

# The following decision has to be made before we've set any env variables,
# otherwise the script will detect our "gst uninstalled" and think it's the
# system-wide install.
if pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'; then
    MODULES="gnonlin gst-editing-services gst-python"
else
    MODULES="gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly gst-plugins-bad gst-ffmpeg gnonlin gst-editing-services gst-python"
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


if pkg-config --exists --print-errors 'gstreamer-1.0 >= 1.1.0.1'; then
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
PYTHONPATH=$MYPITIVI/pygobject:$MYPITIVI/gst-python${PYTHONPATH:+:$PYTHONPATH}:$MYPITIVI/gst-editing-services/bindings/python${PYTHONPATH:+:$PYTHONPATH}
export LD_LIBRARY_PATH=$PITIVI/pygobject/gi/.libs:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$PITIVI/pygobject/gi/.libs:$DYLD_LIBRARY_PATH

export LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH
export GI_TYPELIB_PATH
export PYTHONPATH


# Force build to happen automatically if the folders are missing
# or if the --build parameter is used, or --force-autogen.
# The difference being --force-autogen forces autogen.sh to be run,
# whereas --build only uses it the first time
ready_to_run=0
force_autogen=1

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
elif [ "$1" == "--build" ]; then
    # Only build modules without using autogen if not necessary, to save time
    force_autogen=0
    shift
elif [ "$1" == "--force-autogen" ]; then
    shift
else
    # The folders existed, and the user just wants to set the shell environment
    ready_to_run=1
    force_autogen=0
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
        git fetch origin  # In case you haven't got the latest release tags...
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
        if test ! -f ./configure || [ "$force_autogen" == "1" ]; then
            ./autogen.sh --prefix=$PITIVI/prefix --disable-gtk-doc --with-python=python2
            if [ $? -ne 0 ]; then
                echo "Could not run autogen for $m ; result: $?"
                exit 1
            fi
        else
            echo "autogen has already been run for $m, not running it again"
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
        git fetch origin  # In case you haven't got the latest release tags...
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
        # changed during compilation of the "gstreamer" and "gst-plugins-base"
        # modules, which prevents git pull --rebase from working
        if [ $m == "gstreamer" ] || [ $m == "gst-plugins-base" ]; then
            git checkout -- po
        fi
        if [ $GST_RELEASE_TAG == "master" ]; then
            git pull --rebase
            if [ $? -ne 0 ]; then
                exit 1
            fi
        fi

        if test ! -f ./configure || [ "$force_autogen" == "1" ]; then
            if $BUILD_DOCS; then
                ./autogen.sh
            else
                ./autogen.sh --disable-gtk-doc --disable-docbook
            fi
            if [ $? -ne 0 ]; then
                echo "Could not run autogen for $m ; result: $?"
                exit 1
            fi
        else
            echo "autogen has already been run for $m, not running it again"
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
    if test ! -f ./configure || [ "$force_autogen" == "1" ]; then
        ./autogen.sh
    if [ $? -ne 0 ]; then
        echo "Could not run autogen for Pitivi ; result: $?"
        exit 1
    fi
    else
        echo "autogen has already been run for Pitivi, not running it again"
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
    # Change the looks of the prompt, to help us remember we're in a subshell.
    # If the user has some custom git bash helpers, try preserving them.

    function function_exists {
        FUNCTION_NAME=$1
        [ -z "$FUNCTION_NAME" ] && return 1
        declare -F "$FUNCTION_NAME" > /dev/null 2>&1
        return $?
        }

    if [[ "${BASH_SOURCE[0]}" != "${0}" ]]
    then
      echo "pitivi-git environment is being sourced"
      export PS1="[ptv] $PS1"
    else
      if [ -z "$*" ];
      then
        cd $PITIVI/pitivi
        cp ~/.bashrc /tmp/ptvCustomPS1
        echo "export PS1=[ptv]\ \$PS1" >> /tmp/ptvCustomPS1
        bash --rcfile /tmp/ptvCustomPS1
      else
        /bin/bash -c "$*"
      fi
    fi
fi
