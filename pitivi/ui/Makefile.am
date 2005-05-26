include $(top_srcdir)/common/python.mk

uidir = $(libdir)/pitivi/ui

ui_PYTHON = \
	__init__.py \
	glade.py \
	mainwindow.py \
	projectsettings.py \
	sourcefactories.py \
	timeline.py \
	timelineobjects.py \
	viewer.py

ui_DATA = \
	actions.xml \
	encodingdialog.glade \
	projectsettings.glade

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(ui_DATA)
