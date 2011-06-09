from pitivi.check import initial_checks


missing_deps = initial_checks()
if missing_deps:
    message, detail = missing_deps
    raise Exception("%s\n%s" % (message, detail))
