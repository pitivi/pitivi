sizes = ['16x16', '24x24', '32x32', '512x512', '22x22', '256x256', '48x48']
themedir = join_paths(get_option('datadir'), 'icons/hicolor')

foreach size: sizes
    install_data(join_paths(size, 'pitivi.png'), install_dir: join_paths(themedir, size, 'apps'))
endforeach

install_data('512x512/text-x-xges.png', install_dir: join_paths(themedir, 'scalable/mimetypes'))
