# coding=utf-8

import os
import time
from PyQt4.QtCore import QObject, pyqtSignal, QFile, QIODevice
from PyQt4.QtNetwork import QFtp

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
                    self._data.append( {'ftp':QFtp(self._parent), 'start':0, 'end':size_unit, 'isFinished':False, 'url':urls[i]} )
                elif i == len(urls)-1:
                    self._data.append( {'ftp':QFtp(self._parent), 'start':(size_unit)*i + 1, 'end':self._size, 'isFinished':False, 'url':urls[i]} )
                else:
                    self._data.append( {'ftp':QFtp(self._parent), 'start':(size_unit)*i + 1, 'end':(size_unit)*i , 'isFinished':False, 'url':urls[i]} )
                print "Dans la boucle des taches : i=" +str(i)+" et data=" + str(self._data)
            # Starting all downloads
            compteur = 0
            for data in self._data:
                ftp = data['ftp']
                # On se connecte
                print "Connecting to host : " + str(data['url'].host()) + " on port : " + str(data['url'].port(21))
                ftp.connectToHost(data['url'].host(), data['url'].port(21))
                # Login
                print "Login"
                ftp.login()
                # Creating File
                out = out_file.fileName() + "/" + str(compteur) + ".part"
                print "Open file : " + out
                out = QFile(out)
                if out.open(QIODevice.WriteOnly):
                    print "Lancement du download : " + out.fileName()  +" a partir de : "+ data['url'].path()       
                    ftp.get(data['url'].path(), out , _type)
                # Signaux
                ftp.done.connect(lambda x, i=i: self.download_finished(i, x))
                ftp.dataTransferProgress.connect(self.data_transfer_progress)
                ftp.stateChanged.connect(self.state_changed)
                # Incrémente le compteur
                compteur += 1
                
    def download_finished(self, i, _):
        # On met à jour le transfert qui vient de se finir
        self._data[i]['isFinished'] = True
        # On arrete le FTP
        self._data[i]['ftp'].close()
        # On vérifie que tous les transferts sont finis
        finished = True
        for p in self._data:
            finished = finished and p['isFinished']
        # Si oui, on envoie le signal :)
        if finished:
            print "FINI !!!!!!"
            time.sleep(1)
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
