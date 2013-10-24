AUTOMAKE_OPTIONS = dist-bzip2

SUBDIRS	= bin pitivi common po tests data help

mimedir = $(datadir)/mime/packages
mime_DATA = pitivi.xml

man_MANS = docs/pitivi.1

EXTRA_DIST = \
	NEWS \
	AUTHORS \
	RELEASE \
    pitivi.xml


DISTCLEANFILES =                \
        intltool-extract        \
        intltool-merge          \
        intltool-update

EXTRA_DIST +=                   \
        intltool-extract.in     \
        intltool-merge.in       \
        intltool-update.in      \
        $(man_MANS)

# This rule allows running pitivi uninstalled
locale-uninstalled:
	if test -d po && test -z "$(DESTDIR)"; then \
	    $(MAKE) -C po datadir=../$(top_builddir) install; \
	fi

locale-uninstalled-clean:
	@-rm -rf _trial_temp
	@-rm -rf $(top_builddir)/locale


all-local: locale-uninstalled
clean-local: locale-uninstalled-clean

check-integration:
	cd tests; make check-integration
