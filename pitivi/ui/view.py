from pitivi.receiver import receiver, handler
import controller

class View(object):

    Controller = controller.Controller

    def __init__(self):
        object.__init__(self)
        self._controller = self.Controller(view=self)

## public interface

    def focus(self):
        pass

    def select(self):
        pass

    def activate(self):
        pass

    def normal(self):
        pass
