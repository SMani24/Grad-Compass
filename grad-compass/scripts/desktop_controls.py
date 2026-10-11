"""Desktop shortcuts routed to the workspace, scoped to its Qt window."""
import threading

from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication, QWidget


class DesktopControls(QObject):
    install_requested = pyqtSignal()

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.native = None
        self.installed = threading.Event()
        self.install_requested.connect(self.install)

    @pyqtSlot()
    def install(self):
        from webview.platforms.qt import BrowserView
        self.install_for(BrowserView.instances[self.window.uid])

    def install_for(self, native):
        self.native = native
        QApplication.instance().installEventFilter(self)
        self.installed.set()

    def navigate(self, direction):
        self.native.webview.page().runJavaScript(f"window.GradCompassNavigation?.{direction}()")

    def eventFilter(self, watched, event):
        if self.native is None or self.window.events.closed.is_set():
            return False
        if not isinstance(watched, QWidget) or not (watched is self.native or self.native.isAncestorOf(watched)):
            return False
        if QApplication.instance().activeModalWidget() is not None:
            return False  # Let Escape/cancel work normally inside the close confirmation.
        kind = event.type()
        if kind == QEvent.Type.KeyPress:
            modifiers = event.modifiers()
            if event.key() == Qt.Key.Key_W and modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
                if not event.isAutoRepeat():
                    self.native.close()  # pywebview's native confirmation handles cancellation.
                return True
            if modifiers & Qt.KeyboardModifier.AltModifier and event.key() in (Qt.Key.Key_Left, Qt.Key.Key_Right):
                self.navigate("back" if event.key() == Qt.Key.Key_Left else "forward")
                return True
        if kind in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease) and event.button() in (Qt.MouseButton.BackButton, Qt.MouseButton.ForwardButton):
            if kind == QEvent.Type.MouseButtonRelease:
                self.navigate("back" if event.button() == Qt.MouseButton.BackButton else "forward")
            return True
        return False
