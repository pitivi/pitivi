# Documentation

We use the [Epydoc](http://epydoc.sourceforge.net/manual-fields.html)
annotations to document the method parameters, etc. Most importantly, if
there can be any doubt about the expected type for a method parameter,
use “@type parameter\_name: bla bla” to mention it!

To build the API documentation, simply run:

`epydoc pitivi/ -o `<outputdir>
