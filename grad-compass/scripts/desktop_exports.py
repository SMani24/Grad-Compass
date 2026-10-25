"""Native directory settings invoked explicitly by the current app profile."""
import threading
from pathlib import Path
from PyQt6.QtCore import QObject,pyqtSignal,pyqtSlot,QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QFileDialog,QMessageBox
from web.export_preferences import preference


class DesktopExports(QObject):
    requested=pyqtSignal(object,str,object)
    def __init__(self):
        super().__init__();self.requested.connect(self.perform)

    def action(self,workspace,action):
        if action not in ('change','open','reset'):raise ValueError('Choose Change, Open or Reset')
        answer={'done':threading.Event()};self.requested.emit(workspace,action,answer)
        if not answer['done'].wait(180):raise ValueError('Export-folder action did not finish; retry in Settings')
        if 'error' in answer:raise ValueError(answer['error'])
        return answer['result']

    @pyqtSlot(object,str,object)
    def perform(self,workspace,action,answer):
        try:
            current=preference(workspace)
            if action=='change':
                folder=QFileDialog.getExistingDirectory(None,'Default export folder',current['folder'])
                answer['result']=preference(workspace,folder) if folder else {**current,'cancelled':True}
            elif action=='reset':answer['result']=preference(workspace,reset=True)
            else:
                folder=Path(current['folder'])
                if not folder.is_dir():raise ValueError('This folder does not exist yet. Export a report or choose an existing folder')
                if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder))):raise ValueError('The desktop could not open this folder')
                answer['result']=current
        except (ValueError,OSError) as error:answer['error']=str(error)
        finally:answer['done'].set()
