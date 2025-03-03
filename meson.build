project('pitivi', 'c', version : '2023.03.1', meson_version : '>= 0.46.0')
host_system = host_machine.system()

pymod = import('python')
python = pymod.find_installation(get_option('python'))
pythonver = python.language_version()

# Workaround for https://github.com/mesonbuild/meson/issues/5629
# https://gitlab.freedesktop.org/gstreamer/gst-python/issues/28
python_dep = dependency('python-@0@-embed'.format(pythonver), version: '>= 3.5', required: false)
if not python_dep.found()
  python_dep = python.dependency(version: '>= 3.5')
endif

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


geteenvvar = find_program('getenvvar.py')
cdata = configuration_data()
cdata.set('CONFIGURED_PYTHONPATH',
          run_command(geteenvvar, 'PYTHONPATH').stdout().strip())
cdata.set('CONFIGURED_GI_TYPELIB_PATH',
          run_command(geteenvvar, 'GI_TYPELIB_PATH').stdout().strip())
ld_library_path = 'LD_LIBRARY_PATH'
if host_system == 'darwin'
    ld_library_path = 'DYLD_LIBRARY_PATH'
endif

cdata.set('CONFIGURED_LD_LIBRARY_PATH',
          run_command(python, geteenvvar, ld_library_path).stdout().strip())
cdata.set('CONFIGURED_GST_PLUGIN_PATH',
          run_command(python, geteenvvar, 'GST_PLUGIN_PATH').stdout().strip())
cdata.set('CONFIGURED_GST_PLUGIN_SYSTEM_PATH',
          run_command(python, geteenvvar, 'GST_PLUGIN_SYSTEM_PATH').stdout().strip())
cdata.set('LIBDIR', join_paths(get_option('prefix'), get_option('libdir')))
cdata.set('DATADIR', join_paths(get_option('prefix'), get_option('datadir')))
cdata.set('PACKAGE_NAME', 'Pitivi')
cdata.set('PACKAGE', 'pitivi')
cdata.set('GITVERSION', '')
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
