#!/bin/sh
# ************************************************************
# Autotools For Pitivi-GUI
# 
# Made By Casaxno <casano_g@epita.fr>
# See also : gst-autogen.sh, configure.ac, src/Makefile.am
#
# ============Modifications===================================
#   Author  Date	Version		Description
# ------------------------------------------------------------
#   GC     27/02/2004   0.0.1          Including common files 
#                                      like gst-autogen.sh
#   EH     26/04/2004   0.0.1          Updated
# *************************************************************

DIE=0
package=pitivi
srcfile=src/main.c

##################################     
# Checking Host Operating System #
##################################
 
 if [ $OSTYPE != linux-gnu ]
     then
     echo "OS Only Accepted : linux-gnu"
     exit
 else

###################################    
# Setting Environnement Variables #
###################################

#      if test -z $AUTOMAKE; then 
# 	 export AUTOMAKE=automake 
# 	 export ACLOCAL=aclocal
# 	 if test -z $AUTOCONF; then export AUTOCONF=autoconf; fi
#      else
# 	 echo "Automake not Found : Please Install at least automake-1.7"
# 	 exit
#      fi
  
     
     # CHECK PRESENCE OF GST AUTOTOOLS COMMON FUNCS
     
     if test ! -f common/gst-autogen.sh;
	 then
	 echo "There is something wrong with your source tree."
	 echo "You are missing common/gst-autogen.sh"
	 exit 1
     fi

     . common/gst-autogen.sh

###################################
# Launching Autotools             #
###################################
# This shouldn't be done, you never know where that Makefile comes from...
#      if [ -f Makefile ]
# 	 then
# 	 make distclean ;
#      fi
     
     CONFIGURE_DEF_OPT='--enable-maintainer-mode --enable-debug --enable-DEBUG'
     
     autogen_options $@
     
     ### AUTOTOOLS CHECKING ###

     echo -n "+ check for build tools"
     if test ! -z "$NOCHECK"; then echo " skipped"; else  echo; fi
     version_check "autoconf" \
	 "$AUTOCONF autoconf autoconf-2.54 autoconf-2.53 autoconf-2.52" \
	 "ftp://ftp.gnu.org/pub/gnu/autoconf/" 2 52 || DIE=1
     version_check "automake" \
	 "$AUTOMAKE automake \
	 automake-1.7 automake-1.6 automake-1.5" \
	 "ftp://ftp.gnu.org/pub/gnu/automake/" 1 5 || DIE=1
     version_check "gettext" "" \
	 "ftp://alpha.gnu.org/gnu/" 0 10 35 || DIE=1
     version_check "intltoolize" "" \
	 "ftp://ftp.gnome.org/pub/GNOME/stable/sources/intltool" 0 1 5 || DIE=1
     version_check "libtool" "" \
	 "ftp://ftp.gnu.org/pub/gnu/libtool/" 1 4 0 || DIE=1
     version_check "pkg-config" "" \
	 "http://www.freedesktop.org/software/pkgconfig" 0 8 0 || DIE=1
     die_check $DIE
     
     ### CHECKING PART ###
     
     toplevel_check $srcfile
     autoconf_2_52d_check || DIE=1
     aclocal_check || DIE=1
     autoheader_check || DIE=1
     
     ### RUNNING TOOLS ###
  
     tool_run "libtoolize --copy --force"
     tool_run "$aclocal -I common/m4/"
     tool_run "$autoheader"
     tool_run "$autoconf"
     tool_run "$automake -ac"

     ### CONFIGURE PART ###
     
     echo "+ running configure ... "
     test ! -z "$CONFIGURE_DEF_OPT" && echo "  ./configure default flags: $CONFIGURE_DEF_OPT"
     test ! -z "$CONFIGURE_EXT_OPT" && echo "  ./configure external flags: $CONFIGURE_EXT_OPT"
     ./configure $CONFIGURE_DEF_OPT $CONFIGURE_EXT_OPT || {
	 echo "  configure failed"
	 exit 1
     }
     
     ### END PART COMPILATION ###
     echo "Now type 'make' to compile $package."
     # for go faster enables comments
     # make; 
     # ./src/Pitivi
 fi
 