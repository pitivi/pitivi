AUTOMAKE_OPTIONS = dist-bzip2

SUBDIRS	= bin pitivi common po tests icons

desktopdir = $(datadir)/applications
desktop_in_files = pitivi.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

mimedir = $(datadir)/mime/packages
mime_DATA = pitivi.xml

man_MANS = pitivi.1

EXTRA_DIST = \
	pitivi.spec \
	pitivi.spec.in \
	ChangeLog \
	autogen.sh \
	NEWS \
	AUTHORS \
	RELEASE \
	ABOUT-NLS \
    pitivi.xml


DISTCLEANFILES =                \
        intltool-extract        \
        intltool-merge          \
        intltool-update


CLEANFILES =                    \
        $(desktop_DATA)


EXTRA_DIST +=                   \
        intltool-extract.in     \
        intltool-merge.in       \
        intltool-update.in      \
        $(desktop_in_files)     \
        $(man_MANS)


locale-uninstalled:
	if test -d po; then \
	    $(MAKE) -C po datadir=../$(top_builddir) install; \
	fi

locale-uninstalled-clean:
	@-rm -rf _trial_temp
	@-rm -rf $(top_builddir)/locale


all-local: locale-uninstalled
clean-local: locale-uninstalled-clean

check-integration:
	cd tests; make check-integration
