#!/bin/sh

export PYTHON=python3

package=pitivi

# if no arguments specified then this will be printed
if test -z "$*"; then
  echo "+ checking for autogen.sh options"
  echo "  This autogen script will automatically run ./configure as:"
  echo "  ./configure $@"
  echo "  To pass any additional options, please specify them on the $0"
  echo "  command line."
fi

autoreconf --force --install || exit 1

if test -n "$NOCONFIGURE"; then
  echo "+ skipping configure stage for package $package, as requested."
  echo "+ autogen.sh done."
  exit 0
fi

echo "+ running configure ..."
echo "./configure $@"
./configure "$@" || exit 2

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
