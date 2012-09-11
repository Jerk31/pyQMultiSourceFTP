# coding=utf-8

import os
from PyQt4.QtCore import QString, QObject, pyqtSignal, QFile, SIGNAL, QIODevice
from PyQt4.QtNetwork import QFtp

class MyQFTP(QObject):
    done                    = pyqtSignal(bool)
    stateChanged            = pyqtSignal(int)
    dataTransferProgress    = pyqtSignal(int, int)
    
    def __init__(self, data, number, parent=None):
        QObject.__init__(self)
        self.ftp = QFtp(parent)
        self._data = data
        self._number = number
        # Signaux
        self.ftp.done.connect(self.modifyData)
        self.ftp.stateChanged.connect(self.modifyState)
        self.ftp.dataTransferProgress.connect(self.newProgress)
        
    def connectToHost(self, host, port=21):
        self.ftp.connectToHost(host, port)
        
    def login(self, user = QString(), password = QString()):
        self.ftp.login(user, password)
        
    def get(self, _file, device = None, _type = QFtp.Binary):
        print "GetDownload"
        self.ftp.get(_file, device, _type)
        
    def close(self):
        self.ftp.close()
        
    def modifyData(self, _):
        print "Source " + str(self._number) + " : download terminé!"
        self.data['isFinished'] = True
        self.done.emit(_)
        
    def newProgress(self, read_bytes, total):
        print "Progression du download : source " + str(self._number)
        self.dataTransferProgress.emit(read_bytes, total)
    
    def modifyState(self, state):
        self.stateChanged.emit(state)

class QMultiSourceFTP(QObject):
    done                    = pyqtSignal(bool)
    stateChanged            = pyqtSignal(int)
    dataTransferProgress    = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        QObject.__init__(self)
        # Vars
        self._parent        = parent
        self.ftp            = []
        self._finish        = []
        self._file_parts    = []
        self._urls          = None
        self._size          = 0
        # Debug
        self.state          = -1
    
    # TODO : se débrouiller pour récupérer la taille du fichier...
    def get(self, urls, size, out_file = None, _type = QFtp.Binary):
        print "Entrée dans la fonction"
        if urls:
            print "Entrée dans la boucle"
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
                    self._file_parts.append( {'start':0, 'end':self._size/len(urls), 'isFinished':False} )
                elif i == len(urls)-1:
                    self._file_parts.append( {'start':(self._size/len(urls))*i + 1, 'end':self._size, 'isFinished':False} )
                else:
                    self._file_parts.append( {'start':(self._size/len(urls))*i + 1, 'end':(self._size/len(urls))*i , 'isFinished':False} )
                print "Dans la boucle des taches : i=" +str(i)+" et file_parts=" + str(self._file_parts)
            # Starting all downloads
            for i in range(len(urls)):
                self.ftp.append(MyQFTP(self._file_parts[i], i, self._parent))
                # On se connecte
                print "Connecting to host :" + str(self._urls[i].host()) + " on port : " + str(self._urls[i].port(21))
                self.ftp[i].connectToHost(self._urls[i].host(), self._urls[i].port(21))
                print "Login"
                self.ftp[i].login()
                print "Open the file"
                out = out_file.fileName() + "/" + str(i) + ".part"
                if QFile(out).open(QIODevice.WriteOnly):
                    print "Lancement du download : " + out  +" a partir de : "+ self._urls[i].path()       
                    self.ftp[i].get(self._urls[i].path(), QFile(out) , _type)
                # Signal finish
                self.ftp[i].done.connect(self.checkFinished)
                self.ftp[i].dataTransferProgress.connect(self.avanceeTransfert)
                self.ftp[i].stateChanged.connect(self.changementEtat)
                
    def checkFinished(self):
        finished = True
        # On vérifie que tous les transferts sont finis
        for p in self._file_parts:
            finished = finished and p['isFinished']
        # Si oui, on envoie le signal :)
        if finished:
            print "FINI !!!!!!"
            self.done.emit
            
    def avanceeTransfert(self, read, total):
        print "On avance"
        
    def changementEtat(self, state):
        self.state = state
        if state == 1 or state == 2:
            print "CONNEXION"
        elif state == 3 or state == 4:
            print "TELECHARGEMENT"
