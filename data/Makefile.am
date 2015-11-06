SUBDIRS=icons pixmaps ui renderpresets audiopresets videopresets gstpresets

desktopdir = $(datadir)/applications
desktop_in_files = pitivi.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

appdatadir = $(datadir)/appdata
appdata_in_files = pitivi.appdata.xml.in
appdata_DATA = $(appdata_in_files:.appdata.xml.in=.appdata.xml)
@INTLTOOL_XML_RULE@

CLEANFILES =  \
        $(desktop_DATA) \
        $(appdata_DATA)

EXTRA_DIST = \
        $(desktop_in_files) \
        $(appdata_in_files)
