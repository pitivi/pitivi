tests = \
	test_basic.py

EXTRA_DIST = $(tests) runtests.py

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py
