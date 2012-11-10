
# Please keep the test lists below ordered.

tests = \
	test_basic.py \
	test_binary_search.py \
	test_cache.py \
	test_common.py \
	test_projectmanager.py \
	test_settings.py \
	test_signallable.py \
	test_timeline_undo.py \
	test_undo.py \
	test_utils.py \
	test_system.py \
	test_log.py \
	test_system_gnome.py

integration_tests = \
	test_preset.py \
	test_projectsettings.py

EXTRA_DIST = \
	__init__.py \
	common.py \
	runtests.py \
	$(tests)

clean-local:
	rm -rf *.pyc *.pyo

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py \
		$(tests)

%.check: %
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py $*

check-integration:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py \
		$(integration_tests)
