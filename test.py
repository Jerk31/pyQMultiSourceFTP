# coding=utf-8

import time
from QMultiSourceFTP import QMultiSourceFTP
from PyQt4.QtCore import QUrl, QFile, QTimer

if __name__ == "__main__":
    download = QMultiSourceFTP()
    url = QUrl("ftp://10.31.40.160:2221/dossier1/c_un_test.mp3")
    out_file = QFile("/home/jerk/a_suppr/c_un_test.mp3")
    urls = list()
    urls.append(url)
    download.get(urls, 14950400, out_file)
       
    while True:
        print "Etat : " + str(download.state)
        time.sleep(1)
        
