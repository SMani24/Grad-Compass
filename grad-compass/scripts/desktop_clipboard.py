"""Small Qt clipboard bridge for an explicit Copy action in the local window."""
import threading
from PyQt6.QtCore import QObject,pyqtSignal,pyqtSlot
from PyQt6.QtWidgets import QApplication


class _ClipboardBridge(QObject):
    requested=pyqtSignal(str,object)

    def __init__(self):
        super().__init__();self.requested.connect(self.copy)

    @pyqtSlot(str,object)
    def copy(self,text,done):
        QApplication.clipboard().setText(text);done.set()


class DesktopClipboard:
    def __init__(self):self._bridge=_ClipboardBridge()

    def copy_text(self,text):
        if not isinstance(text,str) or len(text)>32000:raise ValueError('Choose the prepared instructions to copy')
        done=threading.Event();self._bridge.requested.emit(text,done)
        if not done.wait(5):raise ValueError('Copy is unavailable. Select and copy the displayed instructions')
        return True
