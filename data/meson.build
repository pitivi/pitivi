subdir('icons')

install_subdir('pixmaps', install_dir: pkgdatadir)
install_subdir('ui', install_dir: pkgdatadir)
install_subdir('audiopresets', install_dir: pkgdatadir)
install_subdir('videopresets', install_dir: pkgdatadir)
install_subdir('gstpresets', install_dir: pkgdatadir)

desktop_file = i18n.merge_file(
    type: 'desktop',
    output : 'org.pitivi.Pitivi.desktop',
    input : 'org.pitivi.Pitivi.desktop.in',
    po_dir: podir,
    install : true,
    install_dir : join_paths(get_option('datadir'), 'applications'))

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test(
    'validate-desktop',
    desktop_file_validate,
    args: [
      desktop_file.full_path()
    ]
  )
endif

appdata_file = i18n.merge_file(
    type: 'xml',
    output : 'org.pitivi.Pitivi.appdata.xml',
    input : 'org.pitivi.Pitivi.appdata.xml.in',
    po_dir: podir,
    install : true,
    install_dir : join_paths(get_option('datadir'), 'metainfo'))

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test(
    'validate-appdata', appstreamcli,
    args: [
      'validate', '--no-net', '--explain', appdata_file.full_path()
    ]
  )
endif

i18n.merge_file(
    output : 'org.pitivi.Pitivi-mime.xml',
    input : 'org.pitivi.Pitivi-mime.xml.in',
    po_dir: podir,
    data_dirs: itsdir,
    install: true,
    install_dir : join_paths(get_option('datadir'), 'mime/packages'))
