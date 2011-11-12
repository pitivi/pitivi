include $(top_srcdir)/gnome-doc-utils.make

dist-hook: doc-dist-hook

DOC_ID = pitivi
DOC_FIGURES = \
    figures/codecscontainers.jpg \
    figures/fadestep1.png \
    figures/fadestep2.png \
    figures/fadestep3.png \
    figures/filechooser.png \
    figures/hovering.png \
    figures/keyframecurves.png \
    figures/layers.png \
    figures/logo.png \
    figures/mainwindow.png \
    figures/previewsource.png \
    figures/ripple-after.png \
    figures/ripple-before.png \
    figures/roll-after.png \
    figures/roll-before.png \
    figures/ruler.png \
    figures/trimming-individual.png

DOC_PAGES = \
    about.page \
    codecscontainers.page \
    crossfading.page \
    effects.page \
    effectsanimation.page \
    fadeinfadeout.page \
    gstreamer.page \
    importingmpegts.page \
    importing.page \
    index.page \
    insertintimeline.page \
    interface.page \
    keyframecurves.page \
    layers.page \
    license.page \
    mainwindow.page \
    makeselections.page \
    medialibrary.page \
    movearoundtimeline.page \
    othertransitions.page \
    presets.page \
    projectsettings.page \
    rendering.page \
    saveproject.page \
    selectunusedfiles.page \
    splitting.page \
    sysreq.page \
    trimming.page \
    usingclips.page \
    welcomedialog.page

DOC_LINGUAS = de es sl

html:
	mkdir -p html
	yelp-build cache C/*.page
	yelp-build html -o html C/*.page
