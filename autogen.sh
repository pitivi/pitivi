#!/bin/sh

export PYTHON=python3

package=pitivi
srcfile=pitivi/application.py

CONFIGURE_DEF_OPT=''

# if no arguments specified then this will be printed
if test -z "$*"; then
  echo "+ checking for autogen.sh options"
  echo "  This autogen script will automatically run ./configure as:"
  echo "  ./configure $CONFIGURE_DEF_OPT"
  echo "  To pass any additional options, please specify them on the $0"
  echo "  command line."
fi

build_help=true
while getopts disable-help x; do
  build_help=false
done; OPTIND=0

if $build_help; then
  GNOMEDOC=`which yelp-build`
  if test -z $GNOMEDOC; then
    echo "Please intall the yelp-tools package"
    exit 1
  fi
fi

autoreconf --force --install || exit 1

if test -n "$NOCONFIGURE"; then
  echo "+ skipping configure stage for package $package, as requested."
  echo "+ autogen.sh done."
  exit 0
fi

echo "+ running configure ... "
test ! -z "$CONFIGURE_DEF_OPT" && echo "  ./configure default flags: $CONFIGURE_DEF_OPT"
test ! -z "$CONFIGURE_EXT_OPT" && echo "  ./configure external flags: $CONFIGURE_EXT_OPT"
echo

./configure $CONFIGURE_DEF_OPT $CONFIGURE_EXT_OPT || exit 2

# install pre-commit hook for doing clean commits
rm -f .git/hooks/pre-commit
ln -s ../../pre-commit.hook .git/hooks/pre-commit
echo ""
which pre-commit > /dev/null
if [ $? -eq 0  ]; then
  pre-commit install
else
  echo "Please install pre-commit from http://pre-commit.com/ before proposing patches"
  echo ""
fi
