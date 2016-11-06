runtests = find_program('nose2', required : false)

if runtests.found()
    tests = [
        ['Test application module', 'test_application'],
        ['Test check module', 'test_check'],
        ['Test clipproperties', 'test_clipproperties'],
        ['Test common utilities', 'test_common'],
        ['Test logging subsystem', 'test_log'],
        ['Test effects', 'test_effects'],
        ['Test the main window', 'test_mainwindow'],
        ['Test the media library', 'test_media_library'],
        ['Test the misc utilities', 'test_misc'],
        ['Test the pipeline', 'test_pipeline'],
        ['Test the preference dialog', 'test_prefs'],
        ['Test presets', 'test_preset'],
        ['Test the previewer', 'test_previewers'],
        ['Test the project', 'test_project'],
        ['Test rendering', 'test_render'],
        ['Test the keyboard shortcuts', 'test_shortcuts'],
        ['Test system integration', 'test_system'],
        ['Test graphical timeline elements', 'test_timeline_elements'],
        ['Test graphical layers', 'test_timeline_layer'],
        ['Test the graphical timeline', 'test_timeline_timeline'],
        ['Test undo/redo for the project', 'test_undo_project'],
        ['Test the undo subsystem', 'test_undo'],
        ['Test undo/redo in the timeline', 'test_undo_timeline'],
        ['Test utilities', 'test_utils'],
        ['Test the timeline utilities', 'test_utils_timeline'],
        ['Test our compound widget', 'test_widgets'],
    ]

    foreach i: tests
        args = ['-t', meson.source_root(), '-s', meson.current_source_dir()]
        if get_option('enable-xunit')
            xunitfile = '' + i.get(0).underscorify() + '.xunit'
            config = configuration_data()
            config.set('path', xunitfile)
            configure_file(input : 'nose2-junit-xml.cfg.in', configuration : config, output : xunitfile + '.cfg')
            args = args + ['--plugin', 'nose2.plugins.junitxml', '--config', meson.current_build_dir() + '/' + xunitfile + '.cfg']
        endif

        test(i.get(0), runtests, args : args + ['tests.' + i.get(1)])
    endforeach
endif
