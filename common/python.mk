py_compile = $(top_srcdir)/common/py-compile-destdir --destdir $(DESTDIR)

#if HAVE_PYCHECKER
#check-local: $(PYCHECKER_FILES)
#	if test ! -z "$(PYCHECKER_FILES)"; \
#	then \
#		PYTHONPATH=$(top_srcdir):$(top_builddir) \
#		pychecker -Q -F $(top_srcdir)/misc/pycheckerrc \
#			$(PYCHECKER_FILES); \
#	fi
#endif
