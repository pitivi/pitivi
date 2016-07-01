project('pitivi', 'c', version: '0.96.0.1')

python = find_program('python3', required : true)
intltool_merge = find_program('intltool-merge', required : true)
itstool = find_program('itstool', required : true)
msgfmt = find_program('msgfmt', required : true)

python_dep = dependency('python3', version : '>= 3.3')
gst_dep = dependency('gstreamer-1.0', version : '>= 1.8.2')
cairo_dep = dependency('cairo')
pycairo_dep = dependency('py3cairo')

pkgdatadir = get_option('datadir') + '/pitivi'

GITVERSION = run_command('git', 'describe', '--always').stdout().strip()
cdata = configuration_data()
cdata.set('CONFIGURED_PYTHONPATH', '')
cdata.set('CONFIGURED_GI_TYPELIB_PATH', '')
cdata.set('CONFIGURED_LD_LIBRARY_PATH', '')
cdata.set('CONFIGURED_GST_PLUGIN_PATH', '')
cdata.set('LIBDIR', get_option('prefix') + '/' + get_option('libdir'))
cdata.set('DATADIR', get_option('prefix') + '/' + get_option('datadir'))
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
