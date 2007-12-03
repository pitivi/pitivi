AUTOMAKE_OPTIONS = dist-bzip2

SUBDIRS	= bin pitivi common po tests

desktopdir = $(datadir)/applications
desktop_DATA = pitivi.desktop

icondir = $(datadir)/pixmaps
icon_DATA = pitivi.png

EXTRA_DIST = \
	pitivi.spec \
	pitivi.spec.in \
	ChangeLog \
	autogen.sh \
	NEWS \
	AUTHORS \
	RELEASE \
	ABOUT-NLS \
	pitivi.png


DISTCLEANFILES =                \
        intltool-extract        \
        intltool-merge          \
        intltool-update


EXTRA_DIST +=                    \
        intltool-extract.in     \
        intltool-merge.in       \
        intltool-update.in

locale-uninstalled:
	if test -d po; then \
	    $(MAKE) -C po datadir=../$(top_builddir) install; \
	fi

locale-uninstalled-clean:
	@-rm -rf _trial_temp
	@-rm -rf $(top_builddir)/locale


all-local: locale-uninstalled
clean-local: locale-uninstalled-clean
