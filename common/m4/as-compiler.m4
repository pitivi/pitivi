dnl as-compiler.m4 0.0.2
dnl autostars m4 macro for detection of compiler flavour
dnl
dnl thomas@apestaart.org

dnl AS_COMPILER(COMPILER)
dnl will set COMPILER to
dnl - gcc
dnl - forte
dnl - (empty) if no guess could be made

AC_DEFUN([AS_COMPILER],
[
  as_compiler=
  AC_MSG_CHECKING(for compiler flavour)

  dnl is it gcc ?
  if test "x$GCC" = "xyes"; then
    as_compiler="gcc"
  fi

  dnl is it forte ?
  AC_TRY_RUN([
int main
(int argc, char *argv[])
{
#ifdef __sun
  return 0;
#else
  return 1;
#endif
}
  ], as_compiler="forte", ,)

  if test "x$as_compiler" = "x"; then
    AC_MSG_RESULT([unknown !])
  else
    AC_MSG_RESULT($as_compiler)
  fi
  [$1]=$as_compiler
])
