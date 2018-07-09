themedir = join_paths(get_option('datadir'), 'icons/hicolor')

sizes = ['16x16', '22x22', '24x24', '32x32', '48x48', '256x256', '512x512']
foreach size: sizes
    install_data(join_paths('hicolor', size, 'apps/org.pitivi.Pitivi.png'), install_dir: join_paths(themedir, size, 'apps'))
endforeach

install_data('hicolor/symbolic/apps/org.pitivi.Pitivi-symbolic.svg', install_dir: join_paths(themedir, 'symbolic/apps'))
