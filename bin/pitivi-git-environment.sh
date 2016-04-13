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

# Change DEFAULT_GST_VERSION to a number greater than the last known release
# if you prefer to work with the "master" branch of everything.
# In that case, the script will automatically "pull --rebase" modules.
DEFAULT_GST_VERSION="1.8.0"

GST_RELEASE_TAG=${GST_RELEASE_TAG:-$DEFAULT_GST_VERSION}
GST_MIN_VERSION=${GST_MIN_VERSION:-$DEFAULT_GST_VERSION}

# If you care about building the GStreamer/GES developer API documentation:
BUILD_DOCS=false

# Here are some dependencies for building GStreamer and GES. If they're missing,
# we'll fetch the git repositories at the given version tag and compile.
# If you set those variables to "master", it will grab the latest dev version
GLIB_RELEASE_TAG="2.34.2" # "gobject-introspection" needs glib > 2.32
PYGOBJECT_RELEASE_TAG="3.8.0"
GOBJECT_INTROSPECTION_MINIMUM_VERSION="1.34.2"
GOBJECT_INTROSPECTION_RELEASE_TAG="GOBJECT_INTROSPECTION_$(echo $GOBJECT_INTROSPECTION_MINIMUM_VERSION | tr '.' '_')"

# If you want to run the development version of Pitivi:
export PITIVI_DEVELOPMENT=1

#
# Everything below this line shouldn't be edited!
#

export PITIVI_PYTHON=python3
export PYTHON=${PITIVI_PYTHON}

# The root of the Pitivi dev environment.
PITIVI=$MYPITIVI

# Some built libraries might be installed here,
# not the normal $MODULES though, see below.
PITIVI_PREFIX=$PITIVI/prefix

if ! pkg-config glib-2.0 --atleast-version=$GLIB_RELEASE_TAG; then
    echo "Using a local build of glib"
    MODULE_GLIB="glib"
else
    echo "Using system-wide glib"
fi

MODULES_CORE=""
if ! pkg-config gobject-introspection-1.0 --atleast-version=$GOBJECT_INTROSPECTION_MINIMUM_VERSION; then
    echo "Using a local build of gobject-introspection-1.0"
    MODULES_CORE="${MODULE_GLIB} gobject-introspection"
else
    echo "Using system-wide gobject-introspection-1.0"
fi

if $PYTHON -c "import gi; gi.check_version('${PYGOBJECT_RELEASE_TAG}')" &> /dev/null; then
    echo "Using system-wide pygobject"
    # Hack around PYTHONPATH ordering to support gi overrides
    PYTHONPATH=$($PYTHON -c 'import gi; print(gi._overridesdir)')/../../:$PYTHONPATH
else
    echo "Using a local build of pygobject"
    PYTHONPATH=$MYPITIVI/pygobject:$PYTHONPATH
    MODULES_CORE="${MODULES_CORE} pygobject"
fi

PYTHONPATH=$MYPITIVI/pitivi:$PYTHONPATH
GI_TYPELIB_PATH=$MYPITIVI/pitivi/pitivi/libpitivi:$GI_TYPELIB_PATH
LD_LIBRARY_PATH=$MYPITIVI/pitivi/pitivi/libpitivi/.libs:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}

EXTRA_PATH="$PITIVI/pitivi/bin"
EXTRA_PATH="$EXTRA_PATH:$PITIVI/gst-editing-services/tools"
EXTRA_PATH="$EXTRA_PATH:$PITIVI/gst-editing-services/tests/tools"
EXTRA_PATH="$EXTRA_PATH:$PITIVI/gst-transcoder/build"

# The following decision has to be made before we've set any env variables,
# otherwise the script will detect our "gst uninstalled" and think it's the
# system-wide install.
if pkg-config gstreamer-1.0 --atleast-version=$GST_MIN_VERSION --print-errors; then
    MODULES="gst-editing-services gst-python"
else
    MODULES="gstreamer gst-plugins-base gst-plugins-good gst-plugins-ugly gst-plugins-bad gst-ffmpeg gst-editing-services gst-python gst-transcoder"
    EXTRA_PATH="$EXTRA_PATH:$PITIVI/gstreamer/tools"
    EXTRA_PATH="$EXTRA_PATH:$PITIVI/gst-plugins-base/tools"
fi
EXTRA_PATH="$EXTRA_PATH:$PITIVI/gst-devtools/validate/tools"
EXTRA_PATH="$EXTRA_PATH:$PITIVI_PREFIX/bin"

# Make the built tools available.
export PATH="$EXTRA_PATH:$PATH"

# /some/path: makes the dynamic linker look in . too, so avoid this
LD_LIBRARY_PATH=$PITIVI_PREFIX/lib:${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
DYLD_LIBRARY_PATH=$PITIVI_PREFIX/lib:${DYLD_LIBRARY_PATH:+:$DYLD_LIBRARY_PATH}
GI_TYPELIB_PATH=$PITIVI_PREFIX/share/gir-1.0:${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}
export PKG_CONFIG_PATH="$PITIVI_PREFIX/lib/pkgconfig:$PITIVI/pygobject:$PKG_CONFIG_PATH"


if pkg-config gstreamer-1.0 --atleast-version=$GST_MIN_VERSION --print-errors; then
    echo "Using system-wide GStreamer 1.0"
else
    echo "Using a local build of GStreamer 1.0"
    # GStreamer ffmpeg libraries
    for path in libavformat libavutil libavcodec libpostproc libavdevice; do
        LD_LIBRARY_PATH=$PITIVI/gst-ffmpeg/gst-libs/ext/ffmpeg/$path:$LD_LIBRARY_PATH
        DYLD_LIBRARY_PATH=$PITIVI/gst-ffmpeg/gst-libs/ext/ffmpeg/$path:$DYLD_LIBRARY_PATH
    done

    # GStreamer plugins base libraries
    for path in app audio cdda fft interfaces pbutils netbuffer riff rtp rtsp sdp tag utils video; do
        LD_LIBRARY_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path/.libs:$LD_LIBRARY_PATH
        DYLD_LIBRARY_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
        GI_TYPELIB_PATH=$PITIVI/gst-plugins-base/gst-libs/gst/$path:$GI_TYPELIB_PATH
    done

    # GStreamer plugins bad libraries
    for path in basecamerabinsrc codecparsers uridownloader egl gl insertbin interfaces mpegts; do
        LD_LIBRARY_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path/.libs:$LD_LIBRARY_PATH
        DYLD_LIBRARY_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
        GI_TYPELIB_PATH=$PITIVI/gst-plugins-bad/gst-libs/gst/$path:$GI_TYPELIB_PATH
    done

    # GStreamer core libraries
    for path in base net check controller; do
        LD_LIBRARY_PATH=$PITIVI/gstreamer/libs/gst/$path/.libs:$LD_LIBRARY_PATH
        DYLD_LIBRARY_PATH=$PITIVI/gstreamer/libs/gst/$path/.libs:$DYLD_LIBRARY_PATH
        GI_TYPELIB_PATH=$PITIVI/gstreamer/libs/gst/$path:$GI_TYPELIB_PATH
    done

    LD_LIBRARY_PATH=$PITIVI/gstreamer/gst/.libs:$LD_LIBRARY_PATH
    DYLD_LIBRARY_PATH=$PITIVI/gstreamer/gst/.libs:$DYLD_LIBRARY_PATH
    GI_TYPELIB_PATH=$PITIVI/gstreamer/gst:$GI_TYPELIB_PATH

    LD_LIBRARY_PATH=$PITIVI/gst-devtools/validate/gst/validate/.libs:$LD_LIBRARY_PATH
    DYLD_LIBRARY_PATH=$PITIVI/gst-devtools/validate/gst/validate/.libs:$DYLD_LIBRARY_PATH
    GI_TYPELIB_PATH=$PITIVI/gst-devtools/validate/gst/validate/:$GI_TYPELIB_PATH
    export GST_VALIDATE_APPS_DIR=$GST_VALIDATE_APPS_DIR:$PITIVI/gst-editing-services/tests/validate/
    export GST_VALIDATE_SCENARIOS_PATH=$PITIVI/gst-devtools/validate/data/scenarios/:$GST_VALIDATE_SCENARIOS_PATH
    export GST_VALIDATE_PLUGIN_PATH=$GST_VALIDATE_PLUGIN_PATH:$PITIVI/gst-devtools/validate/plugins/
    export GST_ENCODING_TARGET_PATH=$GST_VALIDATE_PLUGIN_PATH:$PITIVI/pitivi/data/encoding-profiles/

    export PKG_CONFIG_PATH="$PITIVI/gstreamer/pkgconfig\
:$PITIVI/gst-plugins-base/pkgconfig\
:$PITIVI/gst-plugins-good/pkgconfig\
:$PITIVI/gst-plugins-ugly/pkgconfig\
:$PITIVI/gst-plugins-bad/pkgconfig\
:$PITIVI/gst-ffmpeg/pkgconfig\
:$PITIVI/gst-editing-services/pkgconfig\
:$PITIVI/gst-devtools/validate/pkgconfig\
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
:$PITIVI/gst-editing-services/plugins/nle/\
:$PITIVI/gst-editing-services/plugins/ges/\
:$PITIVI/gst-transcoder/build/\
:${GST_PLUGIN_PATH:+:$GST_PLUGIN_PATH}"

export GST_PRESET_PATH="\
$PITIVI/gst-plugins-good/gst/equalizer/\
:$PITIVI/gst-plugins-good/gst/equalizer\
:$PITIVI/gst-plugins-good/ext/jpeg\
:$PITIVI/gst-plugins-good/ext/vpx/\
:$PITIVI/gst-plugins-ugly/ext/x264\
:$PITIVI/gst-plugins-ugly/ext/amrnb\
:$PITIVI/gst-plugins-bad/gst/freeverb\
:$PITIVI/gst-plugins-bad/ext/voamrwbenc\
:$PITIVI/pitivi/data/videopresets/\
:$PITIVI/pitivi/data/audiopresets/\
${GST_PRESET_PATH:+:$GST_PRESET_PATH}"

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
    export MANPATH=$PITIVI/gstreamer/tools:$PITIVI_PREFIX/share/man:$PITIVI/gst-editing-services/docs/man/:$MANPATH

    export GST_VALIDATE_SCENARIOS_PATH=$PITIVI/gst-devtools/validate/data/scenarios/
fi

# And anyway add GStreamer editing services library
export LD_LIBRARY_PATH=$PITIVI/gst-editing-services/ges/.libs:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$PITIVI/gst-editing-services/ges/.libs:$DYLD_LIBRARY_PATH
export PATH=$PITIVI/gst-editing-services/tools:$PATH
GI_TYPELIB_PATH=$PITIVI/gst-editing-services/ges:$GI_TYPELIB_PATH
GI_TYPELIB_PATH=$PITIVI_PREFIX/share/gir-1.0:${GI_TYPELIB_PATH:+:$GI_TYPELIB_PATH}:/usr/lib64/girepository-1.0:/usr/lib/girepository-1.0

# And anyway add GstTranscoder
export LD_LIBRARY_PATH=$PITIVI/gst-transcoder/build/:$LD_LIBRARY_PATH
export DYLD_LIBRARY_PATH=$PITIVI/gst-transcoder/build/:$DYLD_LIBRARY_PATH
export PATH=$PITIVI/gst-transcoder/build/:$PATH
GI_TYPELIB_PATH=$PITIVI/gst-transcoder/build/:$GI_TYPELIB_PATH

# And python
PYTHONPATH=$PYTHONPATH:$MYPITIVI/gst-python:$MYPITIVI/gst-editing-services/bindings/python
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
ready_to_run=1
force_autogen=1
build=false

for i in "$@"; do
    case $i in
        --build)
        force_autogen=0
        ready_to_run=0
        shift
        ;;

        --force-autogen)
        force_autogen=1
        ready_to_run=0
        shift
        ;;

        --devel)
        MODULES="${MODULES} gst-devtools"
        shift
        ;;

        --help)
        cat <<END

--build            - Update and rebuild the needed libraries, if any.
--force-autogen    - Run autogen before building stuff.
--devel            - Also build gst-devtools.

END
        exit
        ;;
    esac
done




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
    ready_to_run=0
fi

if [ "$ready_to_run" != "1" ]; then
    for m in $MODULES_CORE; do
        cd $PITIVI
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
        # Take into account whether the user wants stable releases or "master"
        if [ $m = "glib" ]; then
            # Silly hack for the fact that glib changes the "mkinstalldirs" file
            # when compiling, which prevents git pull --rebase from working
            git checkout -- mkinstalldirs
            git checkout $GLIB_RELEASE_TAG
            if [ $GLIB_RELEASE_TAG = "master" ]; then
                git pull --rebase
                if [ $? -ne 0 ]; then
                    exit 1
                fi
            fi
        elif [ $m = "gobject-introspection" ]; then
            git checkout $GOBJECT_INTROSPECTION_RELEASE_TAG
            if [ $GOBJECT_INTROSPECTION_RELEASE_TAG = "master" ]; then
                git pull --rebase
                if [ $? -ne 0 ]; then
                    exit 1
                fi
            fi
            # Workaround https://bugzilla.gnome.org/show_bug.cgi?id=679438
            export PYTHON=$(which python2)
        elif [ $m = "pygobject" ]; then
            git checkout $PYGOBJECT_RELEASE_TAG
            if [ $PYGOBJECT_RELEASE_TAG = "master" ]; then
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
        if test ! -f ./configure || [ "$force_autogen" = "1" ]; then
            ./autogen.sh --prefix=$PITIVI/prefix --disable-gtk-doc --with-python=$PYTHON
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

        export PYTHON=${PITIVI_PYTHON}
    done

    # Build all the necessary gstreamer modules.
    for m in $MODULES; do
        cd $PITIVI
        echo
        echo "Building $m"
        # If the folder doesn't exist, check out the module. Later on, we will
        # update it anyway.
        if test ! -d $m; then
          if [ "$m" == "gst-transcoder" ]; then
            git clone https://github.com/pitivi/gst-transcoder.git
          else
            git clone git://anongit.freedesktop.org/gstreamer/$m
          fi

          if [ $? -ne 0 ]; then
              echo "Could not checkout $m ; result: $?"
              exit 1
          fi
        fi

        if [ $m = "gst-devtools" ]; then
          cd $m/validate
        else
          cd $m
        fi

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
        if [ $m = "gstreamer" ] || [ $m = "gst-plugins-base" ]; then
            git checkout -- po
        fi
        # Another similar hack because gst-plugins-bad keeps changing
        # common/ and win32/common/:
        if [ $m = "gst-plugins-bad" ]; then
            git checkout -- common
            git checkout -- win32
        fi
        # Yep, another temporary workaround:
        if [ $m = "gst-editing-services" ]; then
            git checkout -- acinclude.m4
        fi

        needs_configure="0"
        if [ "$force_autogen" = "1" ]; then
            needs_configure="1"
        elif [ "$m" == "gst-transcoder" ]; then
            if test ! -f build/build.ninja; then
                needs_configure='1'
            fi
        elif test ! -f ./configure; then
            needs_configure='1'
        fi

        if [ "$needs_configure" = "1" ]; then
            if [ "$m" == "gst-transcoder" ]; then
                ./configure
            else
                # Allow passing per-module arguments when running autogen.
                # For example, specify the following environment variable
                # to pass --disable-eglgles to gst-plugins-bad's autogen.sh:
                #   gst_plugins_bad_AUTOGEN_EXTRA="--disable-eglgles"
                EXTRA_VAR="$(echo $m | sed "s/-/_/g")_AUTOGEN_EXTRA"
                if $BUILD_DOCS; then
                    ./autogen.sh ${!EXTRA_VAR}
                else
                    ./autogen.sh --disable-gtk-doc --disable-docbook ${!EXTRA_VAR}
              fi
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
    done

    # And obviously ... Pitivi itself
    cd $PITIVI
    if test ! -d $PITIVI/pitivi; then
        git clone git://git.gnome.org/pitivi
    fi

    cd pitivi
    if test ! -f ./configure || [ "$force_autogen" = "1" ]; then
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



if [ "$ready_to_run" = "1" ]; then
    # Change the looks of the prompt, to help us remember we're in the
    # Pitivi dev environment.

    if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
        echo "pitivi-git environment is being sourced"
        export PS1="[ptv] $PS1"
    else
        if [ -n "$*" ]; then
            /bin/bash -c "$*"
        else
            function generate_path_and_completion_calls {
                echo "export PATH=$EXTRA_PATH:\$PATH"
                if [[ -d $MYPITIVI/gstreamer ]]; then
                    echo "source $MYPITIVI/gstreamer/data/completions/gst-launch-1.0"
                    echo "source $MYPITIVI/gstreamer/data/completions/gst-inspect-1.0"
                fi
                if [[ -d $MYPITIVI/gst-editing-services ]]; then
                    echo "source $MYPITIVI/gst-editing-services/data/completions/ges-launch-1.0"
                fi
            }

            cd $PITIVI/pitivi
            if [ $SHELL = "/bin/zsh" ]; then
                export ZDOTDIR=$MYPITIVI/.zdotdir
                mkdir -p $ZDOTDIR
                cp ~/.zshrc $ZDOTDIR
                echo "autoload -Uz bashcompinit; bashcompinit" >> $ZDOTDIR/.zshrc
                generate_path_and_completion_calls >> $ZDOTDIR/.zshrc
                echo "PROMPT=[ptv]\ \$PROMPT" >> $ZDOTDIR/.zshrc
                zsh
            elif [ $SHELL = "/bin/bash" ]; then
                RCFILE=$MYPITIVI/.bashrc
                cp ~/.bashrc $RCFILE
                echo "export PS1=[ptv]\ \$PS1" >> $RCFILE
                generate_path_and_completion_calls >> $RCFILE
                /bin/bash --rcfile $RCFILE
            else
                PITIVI_ENV="[ptv]" $SHELL
            fi
        fi
    fi
fi
