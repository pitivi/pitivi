subdir('icons')

install_subdir('pixmaps', install_dir: pkgdatadir)
install_subdir('ui', install_dir: pkgdatadir)
install_subdir('audiopresets', install_dir: pkgdatadir)
install_subdir('videopresets', install_dir: pkgdatadir)
install_subdir('gstpresets', install_dir: pkgdatadir)

custom_target('pitivi.desktop',
    output : 'pitivi.desktop',
    input : 'pitivi.desktop.in',
    command : [intltool_merge, '--desktop-style', podir, '@INPUT@', '@OUTPUT@'],
    install : true,
    install_dir : get_option('datadir') + '/applications')

custom_target('pitivi.appdata.xml',
    output : 'pitivi.appdata.xml',
    input : 'pitivi.appdata.xml.in',
    command : [intltool_merge, '--xml-style', podir, '@INPUT@', '@OUTPUT@'],
    install : true,
    install_dir : get_option('datadir') + '/appdata')
