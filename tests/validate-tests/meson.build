gstvalidate = find_program('gst-validate-launcher', required : false)

if gstvalidate.found()
    run_target('validate', command : [meson.current_source_dir() + '/runtests'])
endif
