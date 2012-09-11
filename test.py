# coding=utf-8

from QMultiSourceFTP import QMultiSourceFtp
from PyQt4.QtCore import QUrl, QFile
from PyQt4.QtGui import QApplication

if __name__ == "__main__":
    app = QApplication([])

    download = QMultiSourceFtp()
    url = QUrl("ftp://localhost:2221/dossier1/c_un_test.mp3")
    out_file = QFile("c_un_test.mp3")
    urls = [url]
    download.get(urls, 14950400, out_file)
       
    app.exec_()
