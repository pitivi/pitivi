##
## configure.in
## 
## Made by guillaume casanova
## Email   <casano_g@epita.fr>
## 
##

# AUTOMAKE_OPTIONS	= foreign
SUBDIRS			= gnonlin src pixmaps
# will come later : pixmaps libs docs

EXTRA_DIST = \
	NEWS \
	NORME \
	README \
	AUTHORS

AUTOMAKE_OPTIONS = dist-bzip2

release: dist
	make @PACKAGE@-@VERSION@.tar.gz.md5
	make @PACKAGE@-@VERSION@.tar.bz2.md5

# generate md5 sum files
%.md5: %
	md5sum $< > $@

rpm: dist
	rpm -ta $(distdir).tar.gz
