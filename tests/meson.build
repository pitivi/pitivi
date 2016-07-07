runtests = find_program('nosetests')

testdir = '@0@'.format(meson.current_source_dir())

tests = [
    ['Test application module', 'test_application.py'],
    ['Test check module', 'test_check.py'],
    ['Test clipproperties', 'test_clipproperties.py'],
    ['Test common utilities', 'test_common.py'],
    ['Test logging subsystem', 'test_log.py'],
    ['Test the main window', 'test_mainwindow.py'],
    ['Test the media library', 'test_media_library.py'],
    ['Test the misc utilities', 'test_misc.py'],
    ['Test the pipeline', 'test_pipeline.py'],
    ['Test the preference dialog', 'test_prefs.py'],
    ['Test presets', 'test_preset.py'],
    ['Test the previewer', 'test_previewers.py'],
    ['Test the project', 'test_project.py'],
    ['Test the keyboard shortcuts', 'test_shortcuts.py'],
    ['Test system integration', 'test_system.py'],
    ['Test graphical timeline elements', 'test_timeline_elements.py'],
    ['Test graphical layers', 'test_timeline_layer.py'],
    ['Test the graphical timeline', 'test_timeline_timeline.py'],
    ['Test undo/redo for the project', 'test_undo_project.py'],
    ['Test the undo subsystem', 'test_undo.py'],
    ['Test undo/redo in the timeline', 'test_undo_timeline.py'],
    ['Test utilities', 'test_utils.py'],
    ['Test the timeline utilities', 'test_utils_timeline.py'],
    ['Test our compound widget', 'test_widgets.py']
]

foreach i: tests
    args = []
    if get_option('enable-xunit')
        args = ['--with-xunit', '--xunit-file=' + i.get(0).underscorify() + '.xunit']
    endif

    test(i.get(0), runtests, args: args + [testdir + '/' + i.get(1)])
endforeach
