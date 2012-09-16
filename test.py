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
    url3 = QUrl("ftp://localhost:2221/dossier3/c_un_test.mp3")
    url4 = QUrl("ftp://localhost:2221/dossier4/c_un_test.mp3")
    out_file = QFile("c_un_test.mp3")
    urls = [url, url2, url3, url4]
    # Signaux
    download.done.connect(download_termine)
    
    
    download.get(urls, out_file)
       
        
    app.exec_()
