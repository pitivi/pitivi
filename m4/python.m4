dnl a macro to check for ability to create python extensions
dnl  AM_CHECK_PYTHON_HEADERS([ACTION-IF-POSSIBLE], [ACTION-IF-NOT-POSSIBLE])
dnl function also defines PYTHON_INCLUDES
AC_DEFUN([AM_CHECK_PYTHON_HEADERS],
[AC_REQUIRE([AM_PATH_PYTHON])
    AC_MSG_CHECKING(for python headers)
    # deduce PYTHON_INCLUDES
    py_prefix=`$PYTHON -c "import sys; print(sys.prefix)"`
    py_exec_prefix=`$PYTHON -c "import sys; print(sys.exec_prefix)"`
    if $PYTHON-config --help 1>/dev/null 2>/dev/null; then
      PYTHON_INCLUDES=`$PYTHON-config --includes 2>/dev/null`
    else
      PYTHON_INCLUDES="-I${py_prefix}/include/python${PYTHON_VERSION}"
      if test "$py_prefix" != "$py_exec_prefix"; then
        PYTHON_INCLUDES="$PYTHON_INCLUDES -I${py_exec_prefix}/include/python${PYTHON_VERSION}"
      fi
    fi
    AC_SUBST(PYTHON_INCLUDES)
    # check if the headers exist
    CPPFLAGS="$CPPFLAGS $PYTHON_INCLUDES"
    AC_PREPROC_IFELSE(
      [AC_LANG_PROGRAM([#include <Python.h>])],
      [AC_MSG_RESULT(found)],
      [AC_MSG_FAILURE(not found)])
])
