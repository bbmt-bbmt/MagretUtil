#! python3
# coding: utf-8

import os
import wmi
import shutil
import win32wnet
# import logging
import uuid
import threading

import glob
import time

# logger = logging.getLogger('MagretUtil.psexec')

REMOTE_PATH = 'c:\\'


def main():
    return


def create_file(filename, file_text):
    """Racourci pour crer un fichier rapidement """
    dir = os.path.dirname(filename)
    if not os.path.exists(dir):
        os.makedirs(dir)
    f = open(filename, "w", encoding='cp850')
    f.write(file_text)
    f.close()


class PsExec:
    """Implémente psexec en python
    il faut avoir les droits pour accéder au partage administratif """

    # variable de classe pour être thread et multiprocess safe
    _filename_lock = threading.Lock()
    _filename_list = []

    def __init__(self, ip, username=None, password=None,
                 remote_path=REMOTE_PATH):
        self.ip = ip
        self.remote_path = remote_path
        self.username = username
        self.password = password
        self.connection = None
        if self.username and self.password:
            self.connection = wmi.WMI(self.ip, user=self.username,
                                      password=self.password)
        else:
            self.connection = wmi.WMI(self.ip)

    def _watcher_process_del(self, process_id, timeout=None):
        """Attend qu'un process se termine et lance une excepction timeout après
         (la méthode watch_for du module wmi ne marche pas tout le temps
        """
        start = time.time()
        while True:
            if not self.connection.Win32_Process(ProcessId=process_id):
                break
            end = time.time()
            if timeout is not None and end - start > timeout:
                raise wmi.x_wmi_timed_out('timeout atteint')
                break
        return

    def run_remote_cmd(self, cmd, timeout=None, no_wait_output=False):
        """Lance la commande dos cmd sur la machine avec un
        timeout si nécessaire
        retourne 1 si la commande n'a pas pu être lancé par wmi
        lance des exceptions si les fichiers output.* ne peuvent
        pas être crées ou copiés
        (output.bat contient la commande à éxécuter
        output.txt contient le résultat de la commande) """

        return_value = 1
        output_data = ''
        pwd = os.getcwd()
        filename = 'output'
        uid = self._get_uid()

        remote_directory = os.path.join(self.remote_path, uid)
        bat_local_path = os.path.join(pwd, uid, filename + '.bat')
        bat_remote_path = os.path.join(remote_directory, filename + '.bat')
        output_remote_path = os.path.join(remote_directory, filename + '.txt')
        output_local_path = os.path.join(pwd, uid, filename + '.txt')
        text = "cd /D " + remote_directory + "\n" + cmd + " > "\
               + output_remote_path + " 2>&1"
        create_file(bat_local_path, text)
        self._net_copy(bat_local_path, remote_directory)
        batcmd = bat_remote_path

        SW_SHOWMINIMIZED = 0
        startup = self.connection.Win32_ProcessStartup.new(ShowWindow=SW_SHOWMINIMIZED)
        process_id, return_value = self.connection.Win32_Process.Create(CommandLine=batcmd, ProcessStartupInformation=startup)


# bonne méthode pour watcher la fin d'un process mais ne marche pas tout le temps
#        watcher = self.connection.watch_for (
#                        notification_type="Deletion",
#                        wmi_class="Win32_Process",
#                        delay_secs=1,
#                        ProcessId=process_id
#                        )
#
#        if timeout == None: watcher()
#        else: watcher(timeout)

        if no_wait_output:
            self._delete(uid)
            return return_value, ''
        self._watcher_process_del(process_id, timeout)

        # Boucle pour être sur que le fichier output.txt est bien crée
        # (laps de temps après la fin du processus ?
        for i in range(1, 3):
            if os.path.exists(self._covert_unc(output_remote_path)):
                break
            time.sleep(i)
        try:
            self._net_copy_back(output_remote_path, output_local_path)
            # cp850 encoding windows
            output_data = open(output_local_path, 'r', errors='replace',
                               encoding='cp850')
            output_data = "".join(output_data.readlines())
        except FileNotFoundError:
            return_value = 1
            # logger.error("La commande n'a retourné aucun résultat, ni erreur. Vérifer votre syntaxe")

        self._net_delete(remote_directory)
        self._delete(uid)

        self._release_uid(uid)
        return return_value, output_data

    def run_remote_file(self, file, param='', timeout=None, no_wait_output=False):
        """copie l'exécutable sur la machine puis le lance avec remote_cmd """
        output_data = None
        return_value = 1
        pwd = os.getcwd()
        uid = self._get_uid()

        dir_remote_path = os.path.join(self.remote_path, uid)
        file_local_path = os.path.join(pwd, file)
        file_remote_path = os.path.join(self.remote_path, "%s\\%s" % (uid, os.path.basename(file)))

        self._net_copy(file_local_path, dir_remote_path)

        return_value, output_data = self.run_remote_cmd(' '.join([file_remote_path, param]),
                                                        timeout, no_wait_output)
        if no_wait_output:
            return return_value, output_data

        self._net_delete(dir_remote_path)
        self._release_uid(uid)
        return return_value, output_data

    def _net_copy(self, source, dest_dir):
        """ Copie fichiers ou repertoire sur la machine. """
        self._wnet_connect()
        dest_dir = self._covert_unc(dest_dir)
        # rajoute le backslash si pas présent.
        if not dest_dir[len(dest_dir) - 1] == '\\':
            dest_dir = ''.join([dest_dir, '\\'])

        # crée destination si n'existe pas.
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
        else:
            # crée le repertoire même si le fichier existe
            # pour lancer une exception.
            if not os.path.isdir(dest_dir):
                os.makedirs(dest_dir)

        # permet d'utiliser * dans source
        for file in glob.glob(source):
            shutil.copy(file, dest_dir)

    def _net_copy_back(self, source_file, dest_file):
        """ Copies fichiers ou repertoire sur la machine. """
        self._wnet_connect()
        source_unc = self._covert_unc(source_file)
        shutil.copyfile(source_unc, dest_file)

    def _wnet_connect(self):
        """Crée la connection avec la ressource """
        unc = ''.join(['\\\\', self.ip])
        try:
            if self.username and self.password:
                win32wnet.WNetAddConnection2(0, None, unc, None, self.username,
                                             self.password)
            else:
                win32wnet.WNetAddConnection2(0, None, unc, None)
        except win32wnet.error as err:
            # deconnecte et reconnect.
            if err.winerror == 1219:
                # win32wnet.WNetCancelConnection2(unc, 0, 0)
                # return self._wnet_connect()
                # si d'autre connection existe avec le même login
                # on continue et on essaie de l'utiliser plutôt que de la canceler
                return
            raise err

    def _covert_unc(self, path):
        """ Convertie path vers UNC path."""
        return ''.join(['\\\\', self.ip, '\\', path.replace(':', '$')])

    def _delete(self, path):
        if os.path.exists(path):
            # Efface l'arborescence si c'est unrepertoire.
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path, ignore_errors=True)
        else:
            # Efface même si n'existe pas pour lancer une exception
            os.remove(path)

    def _net_delete(self, path):
        """ Efface fichiers ou repertoire sur la machine. """
        self._wnet_connect()

        path = self._covert_unc(path)
        self._delete(path)

    def _call_back(self, name):
        """call back qui permet une utilisation souple de la classe:
    classe.dir('/B') """
        def _call_back_return(*arg):
            list_cmd = name.split('_')
            try:
                print(self.run_remote_cmd(" ".join(list_cmd + list(arg)))[1])
            except wmi.x_wmi as w:
                print('erreur de requette wmi (accès, timeout ...)')
                print(w.info)
        return _call_back_return

    def __getattr__(self, name):
        """Permet d'appeller les commandes directement avec l'instance de la
        classe (voir call_back) """
        return self._call_back(name)

    def _get_uid(self):
        """Retourne un identifiant unique qui servira de nom de fichier-
repertoire pour rendre la classe thread et multiprocess safe """
        with PsExec._filename_lock:
            while True:
                filename = 'todel' + str(os.getpid()) + uuid.uuid4().hex
                if filename not in PsExec._filename_list:
                    PsExec._filename_list.append(filename)
                    return filename
                    break

    def _release_uid(self, filename):
        with PsExec._filename_lock:
            PsExec._filename_list.remove(filename)
        return


if __name__ == "__main__":
    main()
