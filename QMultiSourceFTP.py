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
        self._data          = []
        self._urls          = None
        self._size          = 0
        # Debug
        self.state          = -1
    
    # TODO : se débrouiller pour récupérer la taille du fichier...
    def get(self, urls, size, out_file = None, _type = QFtp.Binary):
        print "On a des URLs"
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
            for i in range(len(urls)):
                if i == 0:
                    self._data.append( {'ftp':QFtp(self._parent), 'start':0, 'end':self._size/len(urls), 'isFinished':False} )
                elif i == len(urls)-1:
                    self._data.append( {'ftp':QFtp(self._parent), 'start':(self._size/len(urls))*i + 1, 'end':self._size, 'isFinished':False} )
                else:
                    self._data.append( {'ftp':QFtp(self._parent), 'start':(self._size/len(urls))*i + 1, 'end':(self._size/len(urls))*i , 'isFinished':False} )
                print "Dans la boucle des taches : i=" +str(i)+" et data=" + str(self._data)
            # Starting all downloads
            for i in range(len(urls)):
                # On se connecte
                print "Connecting to host :" + str(self._urls[i].host()) + " on port : " + str(self._urls[i].port(21))
                self._data[i]['ftp'].connectToHost(self._urls[i].host(), self._urls[i].port(21))
                # Login
                print "Login"
                self._data[i]['ftp'].login()
                # Creating File
                out = out_file.fileName() + "/" + str(i) + ".part"
                print "Open file : " + out
                out = QFile(out)
                if out.open(QIODevice.WriteOnly):
                    print "Lancement du download : " + out.fileName()  +" a partir de : "+ self._urls[i].path()       
                    self._data[i]['ftp'].get(self._urls[i].path(), out , _type)
                # Signaux
                self._data[i]['ftp'].done.connect(lambda x, i=i: self.download_finished(i, x))
                self._data[i]['ftp'].dataTransferProgress.connect(self.data_transfer_progress)
                self._data[i]['ftp'].stateChanged.connect(self.state_changed)
                
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
