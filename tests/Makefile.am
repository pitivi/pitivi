
# Don't try to use wildcards to replace the list of tests below.
# http://www.gnu.org/software/automake/manual/automake.html#Wildcards
# Keep this list sorted!
tests =	\
	test_application.py \
	test_check.py \
	test_clipproperties.py \
	test_common.py \
	test_log.py \
	test_mainwindow.py \
	test_misc.py \
	test_prefs.py \
	test_preset.py \
	test_project.py \
	test_projectsettings.py \
	test_system.py \
	test_timeline_timeline.py \
	test_undo.py \
	test_undo_timeline.py \
	test_utils.py \
	test_utils_timeline.py \
	test_widgets.py
# Keep the list sorted!

samples = \
    samples/tears_of_steel.webm

EXTRA_DIST = \
	__init__.py \
	common.py \
	runtests.py \
	$(samples) \
	$(tests)

clean-local:
	rm -rf *.pyc *.pyo

check-local:
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py \
		$(tests)

%.check: %
	@PYTHONPATH=$(top_srcdir):$(PYTHONPATH) $(PYTHON) $(srcdir)/runtests.py $*
