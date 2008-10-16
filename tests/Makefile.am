tests = \
	testHList.py			\
	test_basic.py			\
	test_binary_search.py		\
	test_file_load_save.py		\
	test_timeline_composition.py	\
	test_timeline_objects.py	\
	test_serializable.py		\
	test_signallable.py		\
	test_timeline_source.py		\
	testcomplex.py

EXTRA_DIST = $(tests) runtests.py common.py

clean-local:
	rm testProject.ptv

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py
