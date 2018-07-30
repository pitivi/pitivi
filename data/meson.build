subdir('icons')

install_subdir('pixmaps', install_dir: pkgdatadir)
install_subdir('ui', install_dir: pkgdatadir)
install_subdir('audiopresets', install_dir: pkgdatadir)
install_subdir('videopresets', install_dir: pkgdatadir)
install_subdir('gstpresets', install_dir: pkgdatadir)

custom_target('org.pitivi.Pitivi.desktop',
    output : 'org.pitivi.Pitivi.desktop',
    input : 'org.pitivi.Pitivi.desktop.in',
    command : [intltool_merge, '--desktop-style', podir, '@INPUT@', '@OUTPUT@'],
    install : true,
    install_dir : get_option('datadir') + '/applications')

custom_target('org.pitivi.Pitivi.appdata.xml',
    output : 'org.pitivi.Pitivi.appdata.xml',
    input : 'org.pitivi.Pitivi.appdata.xml.in',
    command : [intltool_merge, '--xml-style', podir, '@INPUT@', '@OUTPUT@'],
    install : true,
    install_dir : get_option('datadir') + '/appdata')
