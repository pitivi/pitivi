
dnl ##  (Taken from pth-1.4.1)
dnl ##
dnl ##  Check whether SVR4/SUSv2 makecontext(2), swapcontext(2) and
dnl ##  friends can be used for user-space context switching
dnl ##
dnl ##  configure.in:
dnl ##     AC_CHECK_MCSC(<success-action>, <failure-action>)
dnl ##

AC_DEFUN([AC_CHECK_MCSC], [
AC_MSG_CHECKING(for usable SVR4/SUSv2 makecontext(2)/swapcontext(2))
AC_CACHE_VAL(ac_cv_check_mcsc, [
AC_TRY_RUN([

#include <stdio.h>
#include <stdlib.h>
#include <ucontext.h>

ucontext_t uc_child;
ucontext_t uc_main;

void child(void *arg)
{
    if (arg != (void *)12345)
        exit(1);
    if (swapcontext(&uc_child, &uc_main) != 0)
        exit(1);
}

int main(int argc, char *argv[])
{
    FILE *fp;
    void *stack;

    /* the default is that it fails */
    if ((fp = fopen("conftestval", "w")) == NULL)
        exit(1);
    fprintf(fp, "no\n");
    fclose(fp);

    /* configure a child user-space context */
    if ((stack = malloc(64*1024)) == NULL)
        exit(1);
    if (getcontext(&uc_child) != 0)
        exit(1);
    uc_child.uc_link = NULL;
    uc_child.uc_stack.ss_sp = (char *)stack+(32*1024);
    uc_child.uc_stack.ss_size = 32*1024;
    uc_child.uc_stack.ss_flags = 0;
    makecontext(&uc_child, child, 2, (void *)12345);

    /* switch into the user context */
    if (swapcontext(&uc_main, &uc_child) != 0)
        exit(1);

    /* Fine, child came home */
    if ((fp = fopen("conftestval", "w")) == NULL)
        exit(1);
    fprintf(fp, "yes\n");
    fclose(fp);

    /* die successfully */
    exit(0);
}
],
ac_cv_check_mcsc=`cat conftestval`,
ac_cv_check_mcsc=no,
ac_cv_check_mcsc=no
)dnl
])dnl
AC_MSG_RESULT([$ac_cv_check_mcsc])
if test ".$ac_cv_check_mcsc" = .yes; then
    ifelse([$1], , :, [$1])
else
    ifelse([$2], , :, [$2])
fi
])dnl

