tests = \
	test_basic.py			\
	test_binary_search.py		\
	test_factories_base.py		\
	test_factories_file.py		\
	test_signallable.py		\
	testcomplex.py			\
	test_pipeline.py		\
	test_action.py			\
	test_undo.py			\
	test_timeline_undo.py		\
	test_integration.py			\
	test_transitions.py			\
	test_alpha_passthrough.py		\
	test_still_image.py			\
	test_gap.py

EXTRA_DIST = $(tests) runtests.py common.py __init__.py

clean-local:
	rm -f testProject.ptv testproject.xptv testproject2.xptv

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) PITIVI_TOP_LEVEL_DIR='$(top_srcdir)' $(PYTHON)\
		$(srcdir)/runtests.py

%.check: %
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py $*

check-integration:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) TEST_INTEGRATION=1 $(PYTHON)\
        $(srcdir)/runtests.py
