runtests = find_program('gst-validate-launcher', required : false)

if runtests.found()
    test('Pitivi unit tests', runtests,
         args : [join_paths(meson.current_source_dir(), 'ptv_testsuite.py')],
         env: ['PYTHONPATH=' + meson.source_root()], timeout: 500)
endif
