##
## configure.in
## 
## Made by guillaume casanova
## Email   <casano_g@epita.fr>
## 
##

# AUTOMAKE_OPTIONS	= foreign
SUBDIRS			= gnl src pixmaps docs ui

EXTRA_DIST = \
	pitivi.spec \
	NEWS \
	NORME \
	README \
	AUTHORS

AUTOMAKE_OPTIONS = dist-bzip2

MMdir = $(datadir)/applications

release: dist
	make @PACKAGE@-@VERSION@.tar.gz.md5
	make @PACKAGE@-@VERSION@.tar.bz2.md5

# generate md5 sum files
%.md5: %
	md5sum $< > $@

rpm: dist
	rpm -ta $(distdir).tar.gz
