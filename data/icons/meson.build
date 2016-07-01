sizes = ['16x16', '24x24', '32x32', '512x512', '22x22', '256x256', '48x48']
themedir = get_option('datadir') + '/icons/hicolor/'

foreach size: sizes
    install_data(size + '/pitivi.png', install_dir: themedir + size + '/apps/')
endforeach
