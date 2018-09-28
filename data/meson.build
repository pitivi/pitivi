subdir('icons')

install_subdir('pixmaps', install_dir: pkgdatadir)
install_subdir('ui', install_dir: pkgdatadir)
install_subdir('audiopresets', install_dir: pkgdatadir)
install_subdir('videopresets', install_dir: pkgdatadir)
install_subdir('gstpresets', install_dir: pkgdatadir)

i18n.merge_file('org.pitivi.Pitivi.desktop',
    type: 'desktop',
    output : 'org.pitivi.Pitivi.desktop',
    input : 'org.pitivi.Pitivi.desktop.in',
    po_dir: podir,
    install : true,
    install_dir : join_paths(get_option('datadir'), 'applications'))

i18n.merge_file('org.pitivi.Pitivi.appdata.xml',
    type: 'xml',
    output : 'org.pitivi.Pitivi.appdata.xml',
    input : 'org.pitivi.Pitivi.appdata.xml.in',
    po_dir: podir,
    install : true,
    install_dir : join_paths(get_option('datadir'), 'metainfo'))

i18n.merge_file('org.pitivi.Pitivi-mime.xml',
    output : 'org.pitivi.Pitivi-mime.xml',
    input : 'org.pitivi.Pitivi-mime.xml.in',
    po_dir: podir,
    data_dirs: itsdir,
    install: true,
    install_dir : join_paths(get_option('datadir'), 'mime/packages'))
