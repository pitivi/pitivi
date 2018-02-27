configure_file(input: 'pitivi.in',
               output: 'pitivi',
               configuration: cdata)

pitivi_bin = '@0@/pitivi'.format(meson.current_build_dir())
install_data(pitivi_bin, install_dir: get_option('bindir'))

# Create `pitivi` in the current dir at build time to be able to
# run uninstalled in the dev env.
run_command('cp', pitivi_bin, meson.current_source_dir())
