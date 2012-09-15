# coding=utf-8

import sys
from QMultiSourceFTP import QMultiSourceFtp
from PyQt4.QtCore import QUrl, QFile
from PyQt4.QtGui import QApplication

def download_termine(b):
    print "Download finish"
    app.exit()

if __name__ == "__main__":
    app = QApplication([])

    download = QMultiSourceFtp()
    url = QUrl("ftp://localhost:2221/dossier1/c_un_test.mp3")
    url2 = QUrl("ftp://localhost:2221/dossier2/c_un_test.mp3")
    out_file = QFile("c_un_test.mp3")
    urls = [url, url2]
    # Signaux
    download.done.connect(download_termine)
    
    
    download.get(urls, 14950400, out_file)
       
        
    app.exec_()
