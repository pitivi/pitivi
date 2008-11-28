from receiver import Receiver, handler
import controller

class View(Receiver):
    
    _controller = None

    Controller = controller.Controller
    
    def __init__(self):
        self._controller = self.Controller(view=self)
        self.normal()

## public interface

    def focus(self):
        pass

    def select(self):
        pass

    def activate(self):
        pass

    def normal(self):
        pass
