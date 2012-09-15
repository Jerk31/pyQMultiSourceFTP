# coding=utf-8

import ftplib
from PyQt4.QtCore import QUrl, QFile, pyqtSignal, QThread

class DownloadPart(QThread):
    """ Cette classe gère le téléchargement d'une partie de fichier """
    """ Elle est basée sur ftplib """
    dataTransferProgress = pyqtSignal(int, int)
    done                 = pyqtSignal(bool, object)
    stateChanged         = pyqtSignal(int)
 
    def __init__(self, url, filename, start, end):
        QThread.__init__(self)
        self.localfile = open(filename , "wb")
        self._start = start
        self.to_read = end - start
        self.url = url
        self.ftp = ftplib.FTP(timeout=60)
        self.canceled = False

    def cancel(self):
        self.canceled = True

    def run(self):
        self.stateChanged.emit(1)
        self.ftp.connect(str(self.url.host()), int(self.url.port(21)))
        self.stateChanged.emit(2)
        self.stateChanged.emit(3)
        self.ftp.login()
        self.stateChanged.emit(4)

        self.ftp.sendcmd("TYPE I")
        data_read = 0
        conn = self.ftp.transfercmd('RETR ' + str(self.url.path()), rest=self._start)
        while data_read < self.to_read and not self.canceled:
            chunk = conn.recv(8192)
            size = min(self.to_read - data_read, len(chunk))
            self.localfile.write(chunk[:size])
            data_read += size
            self.dataTransferProgress.emit(data_read, self.to_read)
        self.stateChanged.emit(5)
        conn.close()
        self.localfile.close()
        self.done.emit(not self.canceled, self)
        self.stateChanged.emit(0)

