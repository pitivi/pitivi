tests = \
	testHList.py			\
	test_basic.py			\
	test_binary_search.py		\
	test_factories_base.py		\
	test_factories_file.py		\
	test_signallable.py		\
	testcomplex.py			\
	testmagnets.py			\
	test_pipeline.py		\
	test_action.py

EXTRA_DIST = $(tests) runtests.py common.py

clean-local:
	rm -f testProject.ptv

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py

%.check: %
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py $*
