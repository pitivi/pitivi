class TransitionListWidget(gtk.VBox):
    """ Widget for listing transitions """

    def __init__(self):
        gtk.VBox.__init__(self)
        self.iconview = gtk.IconView()
        self.treeview = gtk.TreeView()
        self.pack_start(self.iconview)


