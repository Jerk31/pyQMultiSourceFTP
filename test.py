# coding=utf-8

from QMultiSourceFTP import QMultiSourceFTP
from PyQt4.QtCore import QUrl, QFile
from PyQt4.QtGui import QApplication

if __name__ == "__main__":
    app = QApplication([])

    download = QMultiSourceFTP()
    url = QUrl("ftp://localhost:2221/series/sousdossier/sp.avi")
    out_file = QFile("fichier.avi")
    urls = [url]
    download.get(urls, 184549376, out_file)
       
    app.exec_()
