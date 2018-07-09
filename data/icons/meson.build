sizes = ['16x16', '24x24', '32x32', '512x512', '22x22', '256x256', '48x48']
themedir = join_paths(get_option('datadir'), 'icons/hicolor')

foreach size: sizes
    install_data(join_paths(size, 'org.pitivi.Pitivi.png'), install_dir: join_paths(themedir, size, 'apps'))
endforeach
install_data('symbolic/org.pitivi.Pitivi-symbolic.svg', install_dir: join_paths(themedir, 'symbolic/apps'))

install_data('512x512/text-x-xges.png', install_dir: join_paths(themedir, 'scalable/mimetypes'))
