runtests = find_program('gst-validate-launcher', required : false)

if runtests.found()
    runtests_args = [join_paths(meson.current_source_dir(), 'ptv_testsuite.py')]
    if find_program('Xvfb', required: false).found() == false
        warning('Xvfb not found running unit tests')
        runtests_args += ['ptv_testsuite.tests']
    else
        runtests_args += ['--no-display']
    endif


    test('Pitivi unit tests', runtests,
         args : runtests_args,
         env: ['PYTHONPATH=' + meson.source_root()], timeout: 500)
endif
