project('pitivi', 'c', version : '0.98', meson_version : '>= 0.41.0')

python = find_program('python3')
intltool_merge = find_program('intltool-merge')
itstool = find_program('itstool')
msgfmt = find_program('msgfmt')

python_dep = dependency('python3', version : '>= 3.3')
gst_dep = dependency('gstreamer-1.0', version : '>= 1.12.2')
cairo_dep = dependency('cairo')
pycairo_dep = dependency('py3cairo')

gst_transcoder_dep = dependency('gst-transcoder-1.0', version : '>= 1.8.1',
    fallback : ['gst-transcoder', 'gst_transcoder_dep'])

pkgdatadir = join_paths(get_option('datadir'), meson.project_name())

git = find_program('git', required : false)
if git.found()
    GITVERSION = run_command(git, 'describe', '--always').stdout().strip()
else
    GITVERSION = ''
endif


geteenvvar = find_program('getenvvar.py')
cdata = configuration_data()
cdata.set('CONFIGURED_PYTHONPATH',
          run_command(geteenvvar, 'PYTHONPATH').stdout().strip())
cdata.set('CONFIGURED_GI_TYPELIB_PATH',
          run_command(geteenvvar, 'GI_TYPELIB_PATH').stdout().strip())
cdata.set('CONFIGURED_LD_LIBRARY_PATH',
          run_command(geteenvvar, 'LD_LIBRARY_PATH').stdout().strip())
cdata.set('CONFIGURED_GST_PLUGIN_PATH',
          run_command(geteenvvar, 'GST_PLUGIN_PATH').stdout().strip())
cdata.set('CONFIGURED_GST_PLUGIN_SYSTEM_PATH',
          run_command(geteenvvar, 'GST_PLUGIN_SYSTEM_PATH').stdout().strip())
cdata.set('LIBDIR', join_paths(get_option('prefix'), get_option('libdir')))
cdata.set('DATADIR', join_paths(get_option('prefix'), get_option('datadir')))
cdata.set('PACKAGE_NAME', 'Pitivi')
cdata.set('PACKAGE', 'pitivi')
cdata.set('GITVERSION', GITVERSION)
cdata.set('VERSION', meson.project_version())
cdata.set('BUILDDIR', meson.current_build_dir())

coptimizations = shared_library('renderer',
    'pitivi/coptimizations/renderer.c',
    dependencies: [gst_dep, python_dep, pycairo_dep, cairo_dep],
    name_prefix : '',
    install: true,
    install_dir: get_option('libdir') + '/pitivi/python/pitivi/timeline')

pitivi_install_dir = get_option('libdir') + '/pitivi/python/'

run_command(python, '-m', 'compileall', meson.current_source_dir() + '/pitivi')
install_subdir('pitivi', install_dir: pitivi_install_dir)

configure_file(input: 'pitivi/configure.py.in',
               output: 'configure.py',
               configuration: cdata)

configure_file = '@0@/configure.py'.format(meson.current_build_dir())
install_data(configure_file, install_dir: pitivi_install_dir + 'pitivi')

# FIXME work around to get testsuite working
run_command('cp', configure_file, meson.current_source_dir() + '/pitivi')

subdir('bin')
subdir('po')
subdir('data')
if not get_option('disable-help')
    subdir('help')
endif
subdir('tests')
subdir('tests/validate-tests')
