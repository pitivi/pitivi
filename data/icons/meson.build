themedir = join_paths(get_option('datadir'), 'icons/hicolor')

sizes = ['16x16', '22x22', '24x24', '32x32', '48x48', '256x256', '512x512']
foreach size: sizes
    install_data(join_paths('hicolor', size, 'apps/org.pitivi.Pitivi.png'), install_dir: join_paths(themedir, size, 'apps'))
endforeach

install_data('hicolor/symbolic/apps/org.pitivi.Pitivi-symbolic.svg', install_dir: join_paths(themedir, 'symbolic/apps'))

app_icon_sizes = ['16x16', '24x24', '32x32', '48x48', '512x512']
foreach size: app_icon_sizes
    install_data(join_paths('hicolor', size, 'mimetypes/text-x-xges.png'), install_dir: join_paths(themedir, join_paths(size, 'mimetypes')))
endforeach
