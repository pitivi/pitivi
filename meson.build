project('pitivi', 'c', version : '1.90.0.1', meson_version : '>= 0.41.0')
host_system = host_machine.system()

python = find_program('python3')

python_dep = dependency('python3', version : '>= 3.3')
if get_option('build-gst')
    subproject('gst-build', default_options: ['enable_python=true',
        'disable_gstreamer_sharp=true', 'disable_rtsp_server=true',
        'gst-devtools:disable_gtkdoc=true',
        'gst-editing-services:disable_gtkdoc=true',
        'gst-plugins-base:disable_gtkdoc=true',
        'gstreamer:disable_gtkdoc=true',
        ])
endif

gst_dep = dependency('gstreamer-1.0', version : '>= 1.14.1',
    fallback : ['gstreamer', 'gst_dep'])
cairo_dep = dependency('cairo')
pycairo_dep = dependency('py3cairo')

gnome = import('gnome')
i18n = import('i18n')

podir = join_paths(meson.current_source_dir(), 'po')
itsdir = join_paths(meson.current_source_dir(), 'gettext')
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

module_suffix = []
# Python cannot import default .dylib, changed suffix to .so instead
if ['darwin', 'ios'].contains(host_system)
    module_suffix = 'so'
endif

coptimizations = shared_library('renderer',
    'pitivi/coptimizations/renderer.c',
    dependencies: [gst_dep, python_dep, pycairo_dep, cairo_dep],
    name_prefix : '',
    name_suffix: module_suffix,
    install: true,
    install_dir: get_option('libdir') + '/pitivi/python/pitivi/timeline')

pitivi_install_dir = get_option('libdir') + '/pitivi/python/'

run_command(python, '-m', 'compileall', meson.current_source_dir() + '/pitivi')
install_subdir('pitivi', install_dir: pitivi_install_dir)

configure_file(input: 'pitivi/configure.py.in',
               output: 'configure.py',
               configuration: cdata,
               install_dir: pitivi_install_dir + 'pitivi')

configure_file = '@0@/configure.py'.format(meson.current_build_dir())

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
