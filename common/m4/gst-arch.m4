AC_DEFUN([GST_ARCH], [
dnl Set up conditionals for (target) architecture:
dnl ==============================================

dnl Determine CPU
case "x${target_cpu}" in
  xi?86 | xk? | xi?86_64) HAVE_CPU_I386=yes
              AC_DEFINE(HAVE_CPU_I386, 1, [Define if the target CPU is an 
x86])
              dnl FIXME could use some better detection
              dnl       (ie CPUID)
              case "x${target_cpu}" in
                xi386 | xi486) ;;
                *)             AC_DEFINE(HAVE_RDTSC, 1, [Define if RDTSC is available]) ;;
              esac ;;
  xpowerpc*)   HAVE_CPU_PPC=yes
              AC_DEFINE(HAVE_CPU_PPC, 1, [Define if the target CPU is a 
PowerPC]) ;;
  xalpha*)    HAVE_CPU_ALPHA=yes
              AC_DEFINE(HAVE_CPU_ALPHA, 1, [Define if the target CPU is an 
Alpha]) ;;
  xarm*)      HAVE_CPU_ARM=yes
              AC_DEFINE(HAVE_CPU_ARM, 1, [Define if the target CPU is an 
ARM]) ;;
  xsparc*)    HAVE_CPU_SPARC=yes
              AC_DEFINE(HAVE_CPU_SPARC, 1, [Define if the target CPU is a 
SPARC]) ;;
  xmips*)     HAVE_CPU_MIPS=yes
              AC_DEFINE(HAVE_CPU_MIPS, 1, [Define if the target CPU is a 
MIPS]) ;;
  xhppa*)     HAVE_CPU_HPPA=yes
              AC_DEFINE(HAVE_CPU_HPPA, 1, [Define if the target CPU is a 
HPPA]) ;;
  xs390*)     HAVE_CPU_S390=yes
              AC_DEFINE(HAVE_CPU_S390, 1, [Define if the target CPU is a 
S390]) ;;
  xia64*)     HAVE_CPU_IA64=yes
              AC_DEFINE(HAVE_CPU_IA64, 1, [Define if the target CPU is a 
IA64]) ;;
  xm68k*)     HAVE_CPU_M68K=yes
              AC_DEFINE(HAVE_CPU_M68K, 1, [Define if the target CPU is a 
M68K]) ;;
  xx86_64)    HAVE_CPU_X86_64=yes
              AC_DEFINE(HAVE_CPU_X86_64, 1, [Define if the target CPU is a 
x86_64]) ;;
esac

dnl Determine endianness
AC_C_BIGENDIAN

dnl Check for MMX-capable compiler
AC_MSG_CHECKING(for MMX-capable compiler)
AC_TRY_RUN([
#include "include/mmx.h"

main()
{ movq_r2r(mm0, mm1); return 0; }
],
[
HAVE_LIBMMX="yes"
AC_MSG_RESULT(yes)
],
HAVE_LIBMMX="no"
AC_MSG_RESULT(no)
,
HAVE_LIBMMX="no"
AC_MSG_RESULT(no)
)

AM_CONDITIONAL(HAVE_CPU_I386,       test "x$HAVE_CPU_I386" = "xyes")
AM_CONDITIONAL(HAVE_CPU_PPC,        test "x$HAVE_CPU_PPC" = "xyes")
AM_CONDITIONAL(HAVE_CPU_ALPHA,      test "x$HAVE_CPU_ALPHA" = "xyes")
AM_CONDITIONAL(HAVE_CPU_ARM,        test "x$HAVE_CPU_ARM" = "xyes")
AM_CONDITIONAL(HAVE_CPU_SPARC,      test "x$HAVE_CPU_SPARC" = "xyes")
AM_CONDITIONAL(HAVE_CPU_HPPA,       test "x$HAVE_CPU_HPPA" = "xyes")
AM_CONDITIONAL(HAVE_CPU_MIPS,       test "x$HAVE_CPU_MIPS" = "xyes")
AM_CONDITIONAL(HAVE_CPU_S390,       test "x$HAVE_CPU_S390" = "xyes")
AM_CONDITIONAL(HAVE_CPU_IA64,       test "x$HAVE_CPU_IA64" = "xyes")
AM_CONDITIONAL(HAVE_CPU_M68K,       test "x$HAVE_CPU_M68K" = "xyes")
AM_CONDITIONAL(HAVE_CPU_X86_64,     test "x$HAVE_CPU_X86_64" = "xyes")
AM_CONDITIONAL(HAVE_LIBMMX,         test "x$USE_LIBMMX" = "xyes")

])

AC_DEFUN([GST_UNALIGNED_ACCESS], [
  AC_MSG_CHECKING([if unaligned memory access works correctly])
  if test x"$as_cv_unaligned_access" = x ; then
    case $host in
      alpha*|arm*|hp*|mips*|sh*|sparc*|ia64*)
        _AS_ECHO_N([(blacklisted) ])
        as_cv_unaligned_access=no
	;;
      i?86*|powerpc*|m68k*)
        _AS_ECHO_N([(whitelisted) ])
        as_cv_unaligned_access=yes
	;;
    esac
  else
    _AS_ECHO_N([(cached) ])
  fi
  if test x"$as_cv_unaligned_access" = x ; then
    AC_TRY_RUN([
int main(int argc, char **argv)
{
  char array[] = "ABCDEFGH";
  unsigned int iarray[2];
  memcpy(iarray,array,8);
#define GET(x) (*(unsigned int *)((char *)iarray + (x)))
  if(GET(0) != 0x41424344 && GET(0) != 0x44434241) return 1;
  if(GET(1) != 0x42434445 && GET(1) != 0x45444342) return 1;
  if(GET(2) != 0x43444546 && GET(2) != 0x46454443) return 1;
  if(GET(3) != 0x44454647 && GET(3) != 0x47464544) return 1;
  return 0;
}
    ], as_cv_unaligned_access="yes", as_cv_unaligned_access="no")
  fi
  AC_MSG_RESULT($as_cv_unaligned_access)
  if test "$as_cv_unaligned_access" = "yes"; then
    AC_DEFINE_UNQUOTED(HAVE_UNALIGNED_ACCESS, 1,
      [defined if unaligned memory access works correctly])
  fi
])

