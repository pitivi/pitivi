_help_installdir = get_option('datadir') + '/help/C/pitivi'
install_subdir('figures', install_dir: _help_installdir)

foreach help_page: help_pages
    install_data(help_page, install_dir: _help_installdir)
endforeach

