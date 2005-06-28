include $(top_srcdir)/common/python.mk

uidir = $(libdir)/pitivi/python/pitivi/ui

ui_PYTHON = \
	__init__.py \
	exportsettingswidget.py \
	glade.py \
	gstwidget.py \
	mainwindow.py \
	projectsettings.py \
	sourcefactories.py \
	timeline.py \
	timelineobjects.py \
	viewer.py

ui_DATA = \
	actions.xml \
	elementsettingsdialog.glade \
	encodingdialog.glade \
	exportsettingswidget.glade \
	projectsettings.glade

clean-local:
	rm -rf *.pyc *.pyo

EXTRA_DIST = $(ui_DATA)
