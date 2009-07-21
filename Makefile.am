AUTOMAKE_OPTIONS = dist-bzip2

SUBDIRS	= bin pitivi common po tests icons

desktopdir = $(datadir)/applications
desktop_in_files = pitivi.desktop.in
desktop_DATA = $(desktop_in_files:.desktop.in=.desktop)
@INTLTOOL_DESKTOP_RULE@

icondir = $(datadir)/icons/hicolor/48x48/apps
icon_DATA = pitivi.png

mimedir = $(datadir)/mime/packages
mime_DATA = pitivi.xml

EXTRA_DIST = \
	pitivi.spec \
	pitivi.spec.in \
	ChangeLog \
	autogen.sh \
	NEWS \
	AUTHORS \
	RELEASE \
	ABOUT-NLS \
	$(ICON_DATA) \
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
        $(desktop_in_files)


gtk_update_icon_cache = gtk-update-icon-cache -f -t $(datadir)/icons/hicolor
install-data-hook: update-icon-cache
uinstall-hook: update-icon-cache
update-icon-cache:
	@-if test -z "$(DESTDIR)"; then \
		echo "Updating Gtk icon cache."; \
		$(gtk_update_icon_cache); \
	else \
		echo "*** Icon cache not updated.  After (un)install, run this:"; \
		echo "***   $(gtk_update_icon_cache)"; \
	fi


locale-uninstalled:
	if test -d po; then \
	    $(MAKE) -C po datadir=../$(top_builddir) install; \
	fi

locale-uninstalled-clean:
	@-rm -rf _trial_temp
	@-rm -rf $(top_builddir)/locale


all-local: locale-uninstalled
clean-local: locale-uninstalled-clean
