AC_DEFUN([GST_CHECK_MAKECONTEXT], [
  AC_MSG_CHECKING([whether we have makecontext])
  AC_TRY_RUN([
#include <ucontext.h>
#include <stdlib.h>

void test(void)
{
        exit(0);
}

int main(int argc, char *argv[])
{
        ucontext_t ucp;
        int ret;

        ret = getcontext(&ucp);
        if(ret<0)exit(1);

        ucp.uc_stack.ss_sp = malloc(65536);
        ucp.uc_stack.ss_size = 65536;

        makecontext(&ucp,test,0);
        setcontext(&ucp);

        exit(1);
}
], HAVE_MAKECONTEXT="yes", HAVE_MAKECONTEXT="no")
AC_MSG_RESULT($HAVE_MAKECONTEXT)
if test "$HAVE_MAKECONTEXT" = "yes"; then
  AC_DEFINE_UNQUOTED(HAVE_MAKECONTEXT, $HAVE_MAKECONTEXT,
                     [defined if we have makecontext ()])
fi
])
