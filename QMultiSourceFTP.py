# coding=utf-8

import os
import time
import ftplib
import shutil
import codecs
from operator import itemgetter
from PyQt4.QtCore import QObject, pyqtSignal, QFile, QIODevice
from PyQt4.QtNetwork import QFtp

from DownloadPart import DownloadPart
from merge import merge_files

class QMultiSourceFtp(QObject):
    """ Cette classe gère le téléchargement multi-source en utilisant DownloadPart """
    done                    = pyqtSignal(bool)
    stateChanged            = pyqtSignal(int)
    dataTransferProgress    = pyqtSignal(int, int)
    
    def __init__(self, parent=None):
        """ Structure du dico data pour chacun des morceaux du téléchargement :
        [Toujours présent]
        'start'         => l'octet de début du morceau
        'isFinished'    => True si on a fini de télécharger ce morceau
        'out'           => le nom du morceau sur le pc
        [Seulement si non fini]                          
        'end'           => l'octet de fin du morceau                            
        'url'           => l'url qu'il utilise pour se télécharger
        'ftp'           => l'instance de la classe DownloadPart qu'il utilise
        [Seulement si resume]
        'old'           => True si le morceau est un vieux morceau              
        """
        QObject.__init__(self)
        # Vars
        self._parent        = parent
        self._data          = None
        self._size          = 0
        self._out_file      = None
        self._read          = None
    
    def get(self, urls, out_file=None, resume=False):
        self._data = []
        self._out_file = out_file
        if urls:
            # On récupère la taille du fichier distant
            # TODO: Gérer problème de connexion ou de fichier non trouvé.
            t_ftp = ftplib.FTP(timeout=60)
            t_ftp.connect(str(urls[0].host()), str(urls[0].port(21)))
            t_ftp.login()
            t_ftp.sendcmd("TYPE I")
            self._size = t_ftp.size(str(urls[0].path()))
            t_ftp.close()
            self._urls = urls
            # Creating temporary folder
            if not resume:
                try:
                    print "Création du dossier " + str(out_file.fileName())
                    os.mkdir(str(out_file.fileName()))
                except OSError:
                    # On supprime le dossier existant et on en créé un autre
                    try:
                        shutil.rmtree(str(self._out_file.fileName()))
                    except OSError:
                        # C'est pas un dossier, c'est un fichier alors, on le supprime
                        os.remove(str(self._out_file.fileName()))
                    finally:
                        os.mkdir(str(out_file.fileName()))    
                # Dividing the task between the peers
                size_unit = self._size/len(urls)
                for i in range(len(urls)):
                    if i == 0:
                        self._data.append( {'start':0, 'end':size_unit, 'downloaded':0, 'isFinished':False, 'url':urls[i]} )
                    elif i == len(urls)-1:
                        self._data.append( {'start':(size_unit)*i + 1, 'end':self._size, 'downloaded':0, 'isFinished':False, 'url':urls[i]} )
                    else:
                        self._data.append( {'start':(size_unit)*i + 1, 'end':(size_unit)*(i+1) , 'downloaded':0, 'isFinished':False, 'url':urls[i]} )
                    #print "Dans la boucle des taches : i=" +str(i)+" et data=" + str(self._data)
                    
            else:       # Resume download
                # Load du fichier .info
                compteur = 0
                size_unit = self._size/len(urls)
                #print "On ouvre le fichier " + out_file.fileName()+".info"
                with codecs.open(out_file.fileName()+"/infos", "r", "utf-8") as config:
                    conf_read = [ line for line in config ]
                    #print conf_read
                    max_compteur = len(conf_read)
                    #print "Nombre de lignes : " + str(max_compteur)
                    # Lit la config et la met dans le dico
                    for line in conf_read:
                        if "=" in line:
                            #print "Splitting line"
                            name, start = line.split("=")
                            #print "Name = " +str(name) + " and start = " +str(start)
                            self._data.append( {'out':QFile(name), 'start':int(start), 'downloaded':os.path.getsize(name), 'isFinished':True, 'old':True} )
                            # Pour chaque partie regarde à quel bit ça c'est arreté
                            size = os.path.getsize(name)                    
                            # Si on avait pas fini de download, on relance un download :)
                            if size != (size_unit)*(compteur+1):
                                self._data.append( {'out':QFile(out_file.fileName()+"/"+str(max_compteur)+".part"), \
                                                    'start':size, 'end':(size_unit)*(compteur+1), 'downloaded':size, \
                                                    'isFinished':False, 'url':urls[compteur]} )
                                max_compteur += 1        
                            
            # Starting all downloads
            compteur = 0
            # Opening part index file
            config = QFile(str(out_file.fileName())+"/infos")
            if config.open(QIODevice.Append):
                for data in self._data:
                    if 'old' not in data:
                        if 'out' not in data:
                            # Name of the file
                            data['out'] = QFile(out_file.fileName() + "/" + str(compteur) + ".part")
                        # FTP
                        data['ftp'] = DownloadPart(data['url'], data['out'].fileName(), data['start'], data['end'])
                        ftp = data['ftp']
                        # Creating File
                        if data['out'].open(QIODevice.WriteOnly):
                            print "Lancement du download : " + data['out'].fileName()  +" a partir de : "+ data['url'].path()
                            config.write(str(data['out'].fileName()) + "=" + str(data['start']) +"\n")    
                            # Signaux
                            ftp.done.connect(self.download_finished)
                            ftp.dataTransferProgress.connect(self.data_transfer_progress)
                            ftp.stateChanged.connect(self.state_changed)       
                            ftp.start()
                            # Incrémente le compteur
                            compteur += 1
            config.close()
                
    def download_finished(self, _, instance):
        data = None
        # On cherche la bonne data
        data = [d for d in self._data if 'ftp' in d and d['ftp'] == instance][0]
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
            # On fait une jolie liste sortie comme on veut
            new_data = sorted(self._data, key=itemgetter('start')) 
            # On merge
            file_list = [ d['out'].fileName() for d in new_data ]
            merge_files(file_list, self._out_file.fileName()+".new")
            # On vire le répertoire
            shutil.rmtree(str(self._out_file.fileName()))
            # On renomme le fichier
            os.rename(self._out_file.fileName()+".new", self._out_file.fileName())
            # On supprime le fichier des parts s'il existe
            try :
                os.remove(str(out_file.fileName())+"/infos")
            except:
                pass
            print "FINI !!!!!!"
            self.done.emit(_)
            
    def data_transfer_progress(self, read, total, instance):
        # TODO : optimiser tout ça, on ne devrait pas avoir à faire une boucle pour chercher la bonne data :/
        # On cherche la bonne data
        data = [d for d in self._data if 'ftp' in d and d['ftp'] == instance][0]
        data['downloaded'] = read
        # On calcule le total téléchargé
        currently_downloaded = 0
        for d in self._data:
            currently_downloaded += d['downloaded']
        print "On a déjà téléchargé : " + str(currently_downloaded) + " sur : " + str(self._size)
        self.dataTransferProgress.emit(currently_downloaded, self._size)
        
    def state_changed(self, state):
        if state == 1:
            print "CONNEXION"
        elif state == 3:
            print "TELECHARGEMENT"
        self.stateChanged.emit(state)
