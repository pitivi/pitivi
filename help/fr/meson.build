lang = 'fr'

_help_installdir = get_option('datadir') + '/help/' + lang + '/pitivi/'
install_subdir('figures', install_dir: _help_installdir)

mo = custom_target(lang + '.mo',
    output : lang + '.mo',
    input : lang + '.po',
    command : [msgfmt, '@INPUT@', '--output-file', '@OUTPUT@'])

foreach help_page: help_pages
    custom_target(lang + '.' + help_page + '.page',
        output : help_page,
        input : '../C/' + help_page,
        command : [itstool, '-m', mo,'@INPUT@', '--output', '@OUTPUT@'],
        install: true,
        install_dir: get_option('datadir') + '/help/' + lang + '/pitivi/')
endforeach

