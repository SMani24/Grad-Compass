"""Qt 6 report downloads with the server's descriptive suggested filename."""
from pathlib import Path
import re
import threading
from urllib.parse import urlsplit
from PyQt6.QtCore import QObject,pyqtSignal,pyqtSlot
from PyQt6.QtWidgets import QFileDialog


class DesktopDownloads(QObject):
    install_requested=pyqtSignal()

    def __init__(self,window,choose_path=None):
        super().__init__();self.window=window;self.choose_path=choose_path;self.installed=threading.Event();self.native=None
        self.install_requested.connect(self.install)

    @pyqtSlot()
    def install(self):
        from webview.platforms.qt import BrowserView
        self.native=BrowserView.instances[self.window.uid]
        signal=self.native.webview.page().profile().downloadRequested
        try:signal.disconnect(self.native.on_download_requested)
        except (TypeError,RuntimeError):pass
        signal.connect(self.download);self.installed.set()

    def download(self,request):
        source=urlsplit(request.url().toString());origin=urlsplit(self.window.original_url)
        if (source.scheme,source.netloc)!=(origin.scheme,origin.netloc) or not re.fullmatch(r'/api/reports/[a-f0-9]{64}/(pdf|markdown)',source.path):request.cancel();return
        extension='md' if source.path.endswith('/markdown') else 'pdf'
        suggested=request.suggestedFileName()
        if not re.fullmatch(r'[a-z0-9-]+\.'+extension,suggested):suggested='country-report.'+extension
        file_filter='Markdown reports (*.md)' if extension=='md' else 'PDF documents (*.pdf)'
        path=self.choose_path(suggested) if self.choose_path else QFileDialog.getSaveFileName(self.native,'Save country report',suggested,file_filter)[0]
        if not path:request.cancel();return
        target=Path(path)
        if target.suffix.lower()!='.'+extension:target=target.with_suffix('.'+extension)
        request.setDownloadDirectory(str(target.parent));request.setDownloadFileName(target.name);request.accept()
