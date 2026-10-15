"""Optional QA screenshots, captured on Qt's GUI thread."""
from pathlib import Path
import threading

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class PreviewCapture(QObject):
    requested = pyqtSignal(str)

    def __init__(self, window, directory, prefix="2026-10-13-exchange-"):
        super().__init__()
        self.prefix = prefix
        self.window = window
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.complete = threading.Event()
        self.saved = False
        self.requested.connect(self.capture)

    def save(self, name):
        self.complete.clear()
        self.requested.emit(str(self.directory / (self.prefix + name + ".local.png")))
        if not self.complete.wait(10) or not self.saved:
            raise RuntimeError("Could not capture the synthetic review screen")

    @pyqtSlot(str)
    def capture(self, path):
        from webview.platforms.qt import BrowserView
        self.saved = BrowserView.instances[self.window.uid].grab().save(path)
        self.complete.set()
