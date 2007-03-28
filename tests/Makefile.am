tests = \
	test_basic.py			\
	test_timeline_objects.py

EXTRA_DIST = $(tests) runtests.py common.py

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py
