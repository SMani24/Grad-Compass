"""Native close dialog integration check; uses only the synthetic workspace."""
import os
from pathlib import Path
import sys
import threading
import urllib.request

app_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(app_root / 'scripts'))
os.environ['QT_API'] = 'pyqt6'
from PyQt6.QtCore import QEvent, QObject, QTimer, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QMessageBox
import webview
import launch_preview
import preview_checks

class Probe(QObject):
    requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.window = None
        self.dialogs = 0
        self.cancelled = threading.Event()
        self.requested.connect(self.check_cancel)
    @pyqtSlot()
    def check_cancel(self):
        from webview.platforms.qt import BrowserView
        QApplication.instance().installEventFilter(self)
        native = BrowserView.instances[self.window.uid]
        QTest.keyClick(native.webview, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
        self.cancelled.set()
    def eventFilter(self, watched, event):
        if isinstance(watched, QMessageBox) and event.type() == QEvent.Type.Show:
            self.dialogs += 1
            response = QMessageBox.StandardButton.No if self.dialogs == 1 else QMessageBox.StandardButton.Yes
            QTimer.singleShot(30, lambda: watched.done(int(response)))
        return False

probe = Probe()
create_window = webview.create_window
def create_confirmed_window(*args, **kwargs):
    kwargs['confirm_close'] = True
    probe.window = create_window(*args, **kwargs)
    return probe.window
webview.create_window = create_confirmed_window
navigation = preview_checks.verify_navigation
def check_navigation_and_close(window):
    navigation(window)
    probe.requested.emit()
    assert probe.cancelled.wait(10), 'Close confirmation did not finish'
    assert not window.events.closed.is_set(), 'Cancelling unexpectedly closed the app'
    with urllib.request.urlopen(window.get_current_url().split('?')[0] + 'api/workspace', timeout=2) as response:
        assert response.status == 200, 'Server did not survive cancellation'
preview_checks.verify_navigation = check_navigation_and_close
sys.argv = ['launch_preview.py', '--smoke-test']
launch_preview.main()
assert probe.dialogs == 2, probe.dialogs
assert probe.window.events.closed.is_set()
print('Native close confirmation passed: Ctrl+W/No preserves the app; Yes closes it cleanly.')
