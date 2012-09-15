# coding=utf-8

import os
import time
import ftplib
from PyQt4.QtCore import QObject, pyqtSignal, QFile, QIODevice, QThread
from PyQt4.QtNetwork import QFtp

class DownloadPart(QThread):
    """ Cette classe gère le téléchargement d'une partie de fichier """
    """ Elle est basée sur ftplib """
    dataTransferProgress = pyqtSignal(int, int)
    done                 = pyqtSignal(bool)
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
        self.done.emit(not self.canceled)
        self.stateChanged.emit(0)


class QMultiSourceFtp(QObject):
    done                    = pyqtSignal(bool)
    stateChanged            = pyqtSignal(int)
    dataTransferProgress    = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        QObject.__init__(self)
        # Vars
        self._parent        = parent
        self._data          = None
        self._size          = 0
        # Debug
        self.state          = -1
    
    # TODO : se débrouiller pour récupérer la taille du fichier...
    def get(self, urls, size, out_file=None, _type=QFtp.Binary):
        print "On a des URLs"
        self._data = []
        if urls:
            self._urls = urls
            self._size = size
            # Creating temporary folder
            try:
                print "Création du dossier " + str(out_file.fileName())
                os.mkdir(str(out_file.fileName()))
            except OSError:
                print "ERREUR : Dossier déjà existant"
            # Dividing the task between the peers
            size_unit = self._size/len(urls)
            for i in range(len(urls)):
                if i == 0:
                    self._data.append( {'start':0, 'end':size_unit, 'isFinished':False, 'url':urls[i]} )
                elif i == len(urls)-1:
                    self._data.append( {'start':(size_unit)*i + 1, 'end':self._size, 'isFinished':False, 'url':urls[i]} )
                else:
                    self._data.append( {'start':(size_unit)*i + 1, 'end':(size_unit)*i , 'isFinished':False, 'url':urls[i]} )
                print "Dans la boucle des taches : i=" +str(i)+" et data=" + str(self._data)
            # Starting all downloads
            compteur = 0
            for data in self._data:
                # Name of the file
                data['out'] = QFile(out_file.fileName() + "/" + str(compteur) + ".part")
                # FTP
                data['ftp'] = DownloadPart(data['url'], data['out'].fileName(), data['start'], data['end'])
                ftp = data['ftp']
                # Creating File
                if data['out'].open(QIODevice.WriteOnly):
                    print "Lancement du download : " + data['out'].fileName()  +" a partir de : "+ data['url'].path()
                    # Signaux
                    ftp.done.connect(lambda x, i=i: self.download_finished(i, x))
                    ftp.dataTransferProgress.connect(self.data_transfer_progress)
                    ftp.stateChanged.connect(self.state_changed)       
                    ftp.run()
                # Incrémente le compteur
                compteur += 1
                
    def download_finished(self, i, _):
        # On met à jour le transfert qui vient de se finir
        self._data[i]['isFinished'] = True
        # On arrete le FTP
        self._data[i]['ftp'].quit()
        # On vérifie que tous les transferts sont finis
        finished = True
        for p in self._data:
            finished = finished and p['isFinished']
        # Si oui, on envoie le signal :)
        if finished:
            print "FINI !!!!!!"
            self.done.emit(_)
            
    def data_transfer_progress(self, read, total):
        print "On avance : " + str(read) + "/" + str(total)
        self.dataTransferProgress.emit(read, total)
        
    def state_changed(self, state):
        self.state = state
        if state == 1 or state == 2:
            print "CONNEXION"
        elif state == 3 or state == 4:
            print "TELECHARGEMENT"
        self.stateChanged.emit(state)
