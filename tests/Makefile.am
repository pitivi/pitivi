
# Please keep the test lists below ordered.

tests = \
	test_action.py \
	test_alpha_passthrough.py \
	test_basic.py \
	test_binary_search.py \
	test_cache.py \
	test_common.py \
	test_discoverer.py \
	test_encode.py \
	test_etree_formatter.py \
	test_factories_base.py \
	test_factories_file.py \
	test_factories_operation.py \
	test_formatters_base.py \
	test_gap.py \
	test_pipeline_action.py \
	test_pipeline.py \
	test_projectmanager.py \
	test_seeker.py \
	test_settings.py \
	test_signallable.py \
	test_sourcelist.py \
	test_stream.py \
	test_timeline_factory.py \
	test_timeline.py \
	test_timeline_undo.py \
	test_track.py \
	test_transitions.py \
	test_undo.py \
	test_utils.py

integration_tests = \
	test_integration.py \
	test_preset.py \
	test_still_image.py

EXTRA_DIST = \
	__init__.py \
	common.py \
	runtests.py \
	$(tests)

clean-local:
	rm -f testProject.ptv testproject.xptv testproject2.xptv

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py \
		$(tests)

%.check: %
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py $*

check-integration:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py \
		$(integration_tests)
