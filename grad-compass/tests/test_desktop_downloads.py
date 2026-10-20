"""Qt 6 download routing without opening file dialogs or writing user files."""
from types import SimpleNamespace
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from PyQt6.QtCore import QUrl
from desktop_downloads import DesktopDownloads


class Request:
    def __init__(self,url,name='belgium-country-report-2026-10-20-v1.pdf'):self.source=url;self.name=name;self.cancelled=False;self.accepted=False
    def url(self):return QUrl(self.source)
    def suggestedFileName(self):return self.name
    def cancel(self):self.cancelled=True
    def accept(self):self.accepted=True
    def setDownloadDirectory(self,value):self.directory=value
    def setDownloadFileName(self,value):self.filename=value


class DesktopDownloadTests(unittest.TestCase):
    def test_qt6_uses_descriptive_name_and_explicit_chosen_destination(self):
        chosen=[];handler=DesktopDownloads(SimpleNamespace(original_url='http://127.0.0.1:1234/'),lambda name:chosen.append(name) or '/tmp/review/chosen.pdf')
        request=Request('http://127.0.0.1:1234/api/reports/'+'a'*64+'/pdf');handler.download(request)
        self.assertEqual(chosen,[request.name]);self.assertEqual((request.directory,request.filename),('/tmp/review','chosen.pdf'));self.assertTrue(request.accepted)

    def test_cancel_and_foreign_downloads_do_not_write(self):
        handler=DesktopDownloads(SimpleNamespace(original_url='http://127.0.0.1:1234/'),lambda name:None)
        for url in ('https://example.org/test.pdf','http://127.0.0.1:1235/api/reports/'+'a'*64+'/pdf','http://127.0.0.1:1234/assets/test.pdf','http://127.0.0.1:1234/api/reports/'+'a'*64+'/pdf'):
            request=Request(url);handler.download(request);self.assertTrue(request.cancelled);self.assertFalse(request.accepted)


if __name__=='__main__':unittest.main()
