# Preamble

Tips to help debug [pitivi
bundles](http://fundraiser.pitivi.org/download-bundles):

# Run pitivi in GDB inside the pitivi bundes

` # Launch the pitivi bundle environment:`\
` APP_IMAGE_TEST=1 ./pitivi-bundle # Change pitivi-bundle with the name of the bundle you downloaded and extracted. eg. ./pitivi-0.94-x86_64`\
` cd $APPDIR`\
` gdb --args python3 bin/pitivi`
