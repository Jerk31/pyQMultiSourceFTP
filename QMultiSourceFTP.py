# coding=utf-8

import os
import ftplib
import shutil
from operator import itemgetter
from PyQt4.QtCore import QObject, pyqtSignal

from DownloadPart import DownloadPart
from merge import merge_files

class QMultiSourceFtp(QObject):
    """ Cette classe gère le téléchargement multi-source en utilisant
    DownloadPart.
    """
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
        """
        QObject.__init__(self)
        # Vars
        self._parent        = parent
        self._data          = None
        self._size          = 0
        self._out_filename  = None
        self._read          = None
        self._is_downloading= False
        self._urls          = []
        self._url_count     = dict()
        self._blacklist     = []
 
    def _get_size(self, urls):
        # On récupère la taille du fichier distant
        # TODO: Gérer problème de connexion ou de fichier non trouvé.
        t_ftp = ftplib.FTP(timeout=60)
        t_ftp.connect(str(urls[0].host()), str(urls[0].port(21)))
        t_ftp.login()
        t_ftp.sendcmd("TYPE I")
        size = t_ftp.size(str(urls[0].path().toUtf8()))
        t_ftp.close()

        return size

    # Récupère les bouts restants :
    def _get_whites(self):
        whites = []

        chunks = sorted(self._data, key=lambda x: x['start'])
        print "c", chunks
        size = self._size

        if len(chunks) > 0:
            if chunks[0]['start'] > 0:
                whites.append({'start': 0, 'end': chunks[0]['start'],
                        'free': True})
            
            for i in range(len(chunks) - 1):
                if chunks[i]['end'] < chunks[i+1]['start']:
                    whites.append({'start': chunks[i]['end'],
                            'end': chunks[i+1]['start'], 'free': True})
            
            if chunks[-1]['end'] < size:
                whites.append({'start': chunks[-1]['end'], 'end': size,
                        'free': True})
        else:
            whites.append({'start': 0, 'end': size, 'free': True})
        return whites

    def _create_dir(self):
        out_filename = self._out_filename
        try:
            #print("Création du dossier " + str(out_filename))
            os.mkdir(out_filename)
        except OSError:
            # On supprime le dossier existant et on en créé un autre
            try:
                shutil.rmtree(self._out_filename)
            except OSError:
                # C'est pas un dossier, c'est un fichier alors, on le supprime
                os.remove(self._out_filename)
            finally:
                os.mkdir(out_filename)

    def _load_info(self):
        # Lit la config et la met dans le dico
        for line in open(self._out_filename + '/info'):
            if "=" in line:
                #print "Splitting line"
                name, start = line.split("=")
                start = int(start)
                # Pour chaque partie regarde à quel bit ça c'est arreté
                size = os.path.getsize(self._out_filename + '/' + name)

                #print "Name = " +str(name) + " and start = " +str(start)
                self._data.append({'out': name, 'start': start,
                        'end': start + size, 'isFinished': True, 'downloaded': size})

                self._compteur += 1

    def _do_distribution(self):
        # On récupère les morceaux restants à télécharger.
        whites = self._get_whites()
        # On les trie du plus gros au plus petit.
        whites.sort(key=lambda x: x['start'] - x['end'])

        # Pour chaque adresse, on va lui affecter un morceau.
        for url in self._urls:
            affected = False
            # On cherche un morceau libre.
            for w in whites:
                if w['free']:
                    w['url'] = url
                    w['free'] = False
                    w['out'] = str(self._compteur) + '.part'
                    affected = True
                    break

            # Si aucun morceau libre, on partage !
            if not affected:
                whites.sort(key=lambda x: x['start'] - x['end'])
                s = whites[0]['end'] - whites[0]['start']
                # Si le morceau mérite d'être partagé... (arbitraire)
                if s > 1000000:
                    whites.append({'url': url,
                            'start': whites[0]['start'] + s / 2,
                            'end': whites[0]['end'], 'free': False,
                            'out': str(self._compteur) + '.part'})
                    whites[0]['end'] = whites[0]['start'] + s / 2
                else:
                    # Pas assez de chose à partager.
                    break

            self._compteur += 1

        for w in whites:
            self._data.append({'url': w['url'], 'out': w['out'],
                    'start': w['start'], 'end': w['end'], 'isFinished': False})

    def _let_me_help(self, url):
        chunks = sorted([d for d in self._data if not d['isFinished']],
                key=lambda x: x['start'] + x['downloaded'] - x['end'])
        data = chunks[0]
        rest = data['end'] - (data['start'] + data['downloaded'])
        if rest <= 1000000:
            return

        end = data['start'] + data['downloaded'] + rest / 2
        old_end = data['end']
        data['ftp'].set_end(end)
        data['end'] = end

        self._compteur += 1
        data = {'url': url, 'out': str(self._compteur) + '.part', 'start': end,
                        'end': old_end, 'isFinished': False}
        self._data.append(data)
        self._start_download(data)

    def _start_download(self, data):
        # FTP
        ftp = DownloadPart(data['url'], self._out_filename + '/' + data['out'],
                        data['start'], data['end'])
        data['ftp'] = ftp
        data['downloaded'] = 0
        print("Lancement du download : " + data['out'] + " a partir de : " +
                        str(data['url'].path().toUtf8()))
        # Signaux
        ftp.done.connect(self.download_finished)
        ftp.dataTransferProgress.connect(self.data_transfer_progress)
        ftp.stateChanged.connect(self.state_changed)       
        ftp.start()


    def get(self, urls, out_filename, resume=False):
        self._compteur = 0
        self._data = []
        self._out_filename = out_filename
        self._urls = urls

        if not urls:
            return

        self._size = self._get_size(urls)
        # Creating temporary folder
        if resume: # Resume download
            self._load_info()
        else:
            self._create_dir()
         
        self._do_distribution()
        self._start_all()
        self._is_downloading = True
        self._write_config()

    def manage_download(self, new_urls):
        if self._is_downloading:
            for url in new_urls:
                if url not in self._blacklist:
                    self._let_me_help(url)
        
    def _start_all(self):
        # Starting all downloads
        # Opening part index file
        for data in self._data:
            if not data['isFinished']:
                self._start_download(data)

    def _write_config(self):
        config = open(self._out_filename + '/info', 'w')
        for data in self._data:
            config.write(data['out'] + "=" + str(data['start']) +"\n")    
        config.close()
 
    def _merge(self):
        # On fait une jolie liste sortie comme on veut
        new_data = sorted(self._data, key=itemgetter('start'))
        # On merge
        file_list = [self._out_filename + '/' + d['out'] for d in new_data]
        merge_files(file_list, self._out_filename + '.new')
        # On vire le répertoire
        shutil.rmtree(self._out_filename)
        # On renomme le fichier
        os.rename(self._out_filename + '.new', self._out_filename)
        # On supprime le fichier des parts s'il existe

    def download_finished(self, ok, instance):
        #XXX: Gérer correctement le ok !
        print "f", ok, instance

        data = None
        # On cherche la bonne data
        data = [d for d in self._data if 'ftp' in d and d['ftp'] == instance][0]
        # On met à jour le transfert qui vient de se finir
        data['isFinished'] = ok #XXX
        # Si on avait mal fini on incrémente le compteur de l'url
        if not ok:
            # Si ce compteur est déjà égal à 1... blacklist
            if data['url'] in self._url_count and self._url_count[data['url']] == 1:
                self._blacklist.append(data['url'])
                print ("Blacklisted : ", data['url'])
            else:
                self._url_count[data['url']] = 1   
        # On arrete le FTP
        data['ftp'].exit()
        # On vérifie que tous les transferts sont finis
        finished = True
        for p in self._data:
            finished = finished and p['isFinished']
        # Si oui, on merge et on envoie le signal :)
        if finished:
            #TODO reverification avant de merger !

            self._merge()
            print "FINI !!!!!!"
            self.done.emit(False)
        elif data['url'] not in self._blacklist:
            self._let_me_help(data['url'])
        else:
            pass
            
    def data_transfer_progress(self, read, total, instance):
        # TODO : optimiser tout ça, on ne devrait pas avoir à faire une boucle pour
        # chercher la bonne data :/
        # On cherche la bonne data
        data = [d for d in self._data if 'ftp' in d and d['ftp'] == instance][0]
        data['downloaded'] = read
        # On calcule le total téléchargé
        currently_downloaded = 0
        for d in self._data:
            currently_downloaded += d['downloaded']
        #print "On a déjà téléchargé : " + str(currently_downloaded) + " sur : " + str(self._size)
        self.dataTransferProgress.emit(currently_downloaded, self._size)
        
    def state_changed(self, state):
        if state == 1:
            print "CONNEXION"
        elif state == 3:
            print "TELECHARGEMENT"
        self.stateChanged.emit(state)
