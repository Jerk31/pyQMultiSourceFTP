# coding=utf-8

import os
import time
import ftplib
import shutil
from PyQt4.QtCore import QObject, pyqtSignal, QFile, QIODevice
from PyQt4.QtNetwork import QFtp

from DownloadPart import DownloadPart
from merge import merge_files

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
        self._out_file      = None
        self._read          = None
    
    def get(self, urls, out_file=None, _type=QFtp.Binary):
        self._data = []
        self._out_file = out_file
        if urls:
            # On récupère la taille du fichier distant
            t_ftp = ftplib.FTP(timeout=60)
            t_ftp.connect(str(urls[0].host()), str(urls[0].port(21)))
            t_ftp.login()
            t_ftp.sendcmd("TYPE I")
            self._size = t_ftp.size(str(urls[0].path()))
            t_ftp.close()
            self._urls = urls
            # Creating temporary folder
            # TODO : gérer les cas de conflit de dossier déjà existant...
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
                    self._data.append( {'start':(size_unit)*i + 1, 'end':(size_unit)*(i+1) , 'isFinished':False, 'url':urls[i]} )
                #print "Dans la boucle des taches : i=" +str(i)+" et data=" + str(self._data)
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
                    ftp.done.connect(self.download_finished)
                    ftp.dataTransferProgress.connect(self.data_transfer_progress)
                    ftp.stateChanged.connect(self.state_changed)       
                    ftp.start()
                    # Incrémente le compteur
                    compteur += 1
                
    def download_finished(self, _, instance):
        data = None
        # On cherche la bonne data
        for d in self._data:
            if d['ftp'] == instance:
                data = d
        # On met à jour le transfert qui vient de se finir
        data['isFinished'] = True
        # On arrete le FTP
        data['ftp'].exit()
        # On vérifie que tous les transferts sont finis
        finished = True
        for p in self._data:
            finished = finished and p['isFinished']
        # Si oui, on merge et on envoie le signal :)
        if finished:
            file_list = []
            # On merge
            file_list = [ d['out'].fileName() for d in self._data ]
            merge_files(file_list, self._out_file.fileName()+".new")
            # On vire le répertoire
            shutil.rmtree(str(self._out_file.fileName()))
            # On renomme le fichier
            os.rename(self._out_file.fileName()+".new", self._out_file.fileName())
            print "FINI !!!!!!"
            self.done.emit(_)
            
    def data_transfer_progress(self, read, total):
        self._read = read
        print "On avance : " + str(self._read) + "/" + str(self._size)
        self.dataTransferProgress.emit(read, total)
        
    def state_changed(self, state):
        if state == 1:
            print "CONNEXION"
        elif state == 3:
            print "TELECHARGEMENT"
        self.stateChanged.emit(state)
