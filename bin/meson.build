configure_file(input: 'pitivi.in',
               output: 'pitivi',
               configuration: cdata,
               install_dir: get_option('bindir'))

pitivi_bin = '@0@/pitivi'.format(meson.current_build_dir())

# Create `pitivi` in the current dir at build time to be able to
# run uninstalled in the dev env.
run_command('cp', pitivi_bin, meson.current_source_dir())
