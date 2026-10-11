"""Actual Qt input regression checks; run separately with QT_QPA_PLATFORM=offscreen."""
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest

from PyQt6.QtCore import Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QDialog, QWidget

spec = importlib.util.spec_from_file_location("desktop_controls", Path(__file__).resolve().parents[1] / "scripts/desktop_controls.py")
controls_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controls_module)


class NativeWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.child = QWidget(self)
        self.commands = []
        self.close_calls = 0
        self.webview = SimpleNamespace(page=lambda: SimpleNamespace(runJavaScript=self.commands.append))

    def close(self):
        self.close_calls += 1
        return False  # Model a cancelled native close confirmation.


class DesktopControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.native = NativeWindow()
        self.controls = controls_module.DesktopControls(SimpleNamespace(events=SimpleNamespace(closed=threading.Event())))
        self.controls.install_for(self.native)
        self.addCleanup(self.app.removeEventFilter, self.controls)

    def test_mouse_side_buttons_navigate_once_each(self):
        QTest.mouseClick(self.native.child, Qt.MouseButton.BackButton)
        QTest.mouseClick(self.native.child, Qt.MouseButton.ForwardButton)
        self.assertEqual(self.native.commands, ["window.GradCompassNavigation?.back()", "window.GradCompassNavigation?.forward()"])

    def test_alt_arrows_and_ctrl_w_are_handled_inside_app(self):
        QTest.keyClick(self.native.child, Qt.Key.Key_Left, Qt.KeyboardModifier.AltModifier)
        QTest.keyClick(self.native.child, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
        QTest.keyClick(self.native.child, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(len(self.native.commands), 2)
        self.assertEqual(self.native.close_calls, 1)

    def test_shortcuts_do_not_affect_other_windows_or_open_dialogs(self):
        other = QWidget()
        QTest.keyClick(other, Qt.Key.Key_W, Qt.KeyboardModifier.ControlModifier)
        self.assertEqual(self.native.close_calls, 0)
        dialog = QDialog(self.native)
        dialog.setModal(True)
        dialog.show()
        self.app.processEvents()
        QTest.mouseClick(self.native.child, Qt.MouseButton.BackButton)
        self.assertEqual(self.native.commands, [])
        dialog.hide()


if __name__ == "__main__":
    unittest.main()
