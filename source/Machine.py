#! python3
# coding: utf-8

import socket
import struct
import win32net
import win32netcon
import pywintypes
import wmi as WmiModule
import re
import os
import subprocess
# import logging
import Psexec

from colorama import Fore

from var_global import fix_str

# logger = logging.getLogger("MagretUtil.Machine")

# Constantes
ALLUME = 1
ETEINT = 0
REMOTE_PATH = 'c:\\'


class Machine:
    """Class qui représente un ordi et son état
(allumé-éteint-erreur-ip-mac) """

    def __init__(self, name):
        self.name = name
        self.etat = ETEINT
        self.ip = None
        self.mac = None
        self._vnc = {}
        self.message_erreur = ""
        self.last_output_cmd = ""
        self.update_etat()
        return

    def wol(self):
        """ wake on lan """
        if self.etat == ALLUME:
            return
        mac = self.mac
        if mac is None:
            self.message_erreur += "L'adresse mac n'est pas défini\n"
            # logger.warning("L'adresse mac n'est pas défini")
            return

        if len(mac) == 12:
            pass
        elif len(mac) == 12 + 5:
            sep = mac[2]
            mac = mac.replace(sep, '')
        else:
            self.message_erreur += "Format d'adresse mac incorrect\n"
            # logger.warning("Format d'adresse mac incorrect")
            return

        # Construction du paquet magique
        data = ''.join(['FFFFFFFFFFFF', mac * 16])
        send_data = b''

        for i in range(0, len(data), 2):
            send_data = b''.join([send_data,
                                  struct.pack('B', int(data[i: i + 2], 16))])

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # sock.bind(('192.168.1.20',0))
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(send_data, ('<broadcast>', 0))
        sock.sendto(send_data, ('<broadcast>', 7))
        sock.sendto(send_data, ('<broadcast>', 9))
        return

    def shutdown(self):
        if self.etat == ALLUME:
            subprocess.call(["shutdown", "/m", '\\\\' + self.name, "/s", "/f", "/t", "0"],
                            stderr=subprocess.DEVNULL)
            self.etat = ETEINT
        return

    def run_remote_cmd(self, cmd, timeout=None, no_wait_output=False):
        """Lance une commande dos sur la machine
        Utilise PsExec """
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)

            result, output_data = _psexec.run_remote_cmd(cmd,
                                                         timeout,
                                                         no_wait_output)
            if result == 0:
                self.last_output_cmd = output_data
            else:
                self.message_erreur += "La commande %s n'a pas pu être lancé à distance\n" % cmd
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
            # logger.error(self.name + ": " + str(p))
        except WmiModule.x_wmi as w:
            self.message_erreur += "Erreur wmi: %s \n" % w.info
            if w.com_error is not None:
                self.message_erreur += fix_str(w.com_error.strerror)
            # logger.error(self.name + ": " + str(w))
        finally:
            _psexec = None
        return

    def run_remote_file(self, file, param,
                        timeout=None, no_wait_output=False):
        """Lance un fichier executable dos sur la machine
        Utilise PsExec """
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
            result, output_data = _psexec.run_remote_file(file, param, timeout,
                                                          no_wait_output)
            if result == 0:
                self.last_output_cmd = output_data
            else:
                self.message_erreur += "Le fichier %s n'a pas pu être lancé à distance\n" % file
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
            # logger.error(self.name + ": " + str(p))
        except WmiModule.x_wmi as w:
            self.message_erreur += "erreur wmi: %s \n" % w.info
            if w.com_error is not None:
                self.message_erreur += fix_str(w.com_error.strerror)

            # logger.error(self.name + ": " + str(w))
        except FileNotFoundError as f:
            self.message_erreur += "Le fichier %s n'existe pas \n" % f.filename
            # logger.error(self.name + ": " + str(f))
        finally:
            _psexec = None
        return

    def vnc_open(self):
        if self.etat == ETEINT:
            return
        self.vnc_close()
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
            self._vnc['uid'] = _psexec._get_uid()
            remote_directory = os.path.join(_psexec.remote_path, self._vnc['uid'])
            vnc_file = ['vnc\\winvnc.exe', 'vnc\\UltraVNC.ini', 'vnc\\vnchooks.dll']

            for file in vnc_file:
                _psexec._net_copy(file, remote_directory)

            cmd_kill = os.path.join(remote_directory, 'winvnc.exe -kill')
            cmd_run = os.path.join(remote_directory, 'winvnc.exe')
            cmd_connect = os.path.join(remote_directory,
                                       'winvnc.exe -connect ' + self.name)

            SW_SHOWMINIMIZED = 0
            startup = _psexec.connection.Win32_ProcessStartup.new(ShowWindow=SW_SHOWMINIMIZED)
            _psexec.connection.Win32_Process.Create(CommandLine=cmd_kill,
                                                    ProcessStartupInformation=startup)
            self._vnc['server_pid'], return_value = _psexec.connection.Win32_Process.Create(CommandLine=cmd_run, ProcessStartupInformation=startup)
            _psexec.connection.Win32_Process.Create(CommandLine=cmd_connect,
                                                    ProcessStartupInformation=startup)
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
            # logger.error(self.name + ": " + str(p))
        except WmiModule.x_wmi as w:
            self.message_erreur += "Erreur wmi: %s \n" % w.info
            if w.com_error is not None:
                self.message_erreur += fix_str(w.com_error.strerror)
            # logger.error(self.name + ": " + str(w))
        except FileNotFoundError as f:
            self.message_erreur += "Le fichier %s n'existe pas" % f.filename
        finally:
            _psexec = None
        return

    def vnc_close(self):
        if self.etat == ETEINT:
            return
        if self._vnc:
            try:
                _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
                remote_directory = os.path.join(_psexec.remote_path, self._vnc['uid'])
                cmd = os.path.join(remote_directory, 'winvnc.exe -kill')
                SW_SHOWMINIMIZED = 0
                startup = _psexec.connection.Win32_ProcessStartup.new(ShowWindow=SW_SHOWMINIMIZED)
                _psexec.connection.Win32_Process.Create(CommandLine=cmd,
                                                        ProcessStartupInformation=startup)
                _psexec._watcher_process_del(self._vnc['server_pid'])
                _psexec.run_remote_cmd('rd /s /q %s' % remote_directory)
            except PermissionError:
                self.message_erreur += "Vous n'avez pas les droits administrateur\n"
                # logger.error(self.name + ": " + str(p))
            except WmiModule.x_wmi as w:
                self.message_erreur += "Erreur wmi: %s \n" % w.info
                if w.com_error is not None:
                    self.message_erreur += fix_str(w.com_error.strerror)
                # logger.error(self.name + ": " + str(w))
            finally:
                _psexec._release_uid(self._vnc['uid'])
                self._vnc = {}
                _psexec = None
        subprocess.call(['taskkill', "/F", "/S", self.name, "/IM", "winvnc.exe"],
                        stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        return

    def put(self, file_path, dir_path):
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
            _psexec._net_copy(file_path, dir_path)
        except FileExistsError:
            self.message_erreur += "le fichier existe déja"
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
        finally:
            _psexec = None
        return

    def ping(self):
        try:
            result_ping = subprocess.check_output(["ping", "-n", " 1", "-w", " 1000", "-4", self.name],
                                                  stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            self.etat = ETEINT
            return
        self.etat = ALLUME
        result_ping = result_ping.decode('cp850', errors='ignore')
        try:
            match = re.search(r'[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}',
                              result_ping)
            self.ip = match.group(0)
        except IndexError:
            self.message_erreur += "erreur lors de la récupération de l'ip\n"
            # logger.warning(self.name + ": " + str(i))
        return

    def init_mac(self):
        if self.etat == ALLUME:
            try:
                wmi = WmiModule.WMI(self.name)
                wmi_net_configs = wmi.Win32_NetworkAdapterConfiguration()
                for net_config in wmi_net_configs:
                    if self.name == net_config.DnsHostName:
                        self.mac = net_config.MACAddress

                # si l'adresse mac est trouvé on l'écrit dans un fichier
                # si le fichier n'existe pas
                if self.mac is not None:
                    path = os.path.join('mac', self.name + '.txt')
                    if os.path.isdir('mac') and not os.path.isfile(path):
                        with open(path, 'w') as f:
                            f.write(self.mac)
            except WmiModule.x_wmi as w:
                self.message_erreur += self.name + " erreur wmi: %s \n" % w.info
                if w.com_error is not None:
                    self.message_erreur += fix_str(w.com_error.strerror)

        if self.etat == ETEINT:
            try:
                # si le fichier qui stocke l'adresse mac existe,
                # on tente de le récupérer
                with open('mac\\' + self.name + '.txt', 'r') as f:
                    self.mac = f.readline().strip('\n')
                    return
            except FileNotFoundError:
                pass
        return

    def update_etat(self):
        """met à jour la machine :
efface les erreurs, met à jour l'état, l'ip """
        self.message_erreur = ''
        self.last_output_cmd = ''
        self.ping()
        self.init_mac()
        return

    def lister_users(self):
        """liste les utilisateurs et retourne un tableau {nom_user:état}
        état peut être degraded ou ok suivant que le compte est activé ou non """
        decalage = len(self.name) + 1
        users = []
        if self.etat == ALLUME:
            try:
                wmi = WmiModule.WMI(self.name)
                wmi_UserAccount = wmi.Win32_UserAccount(LocalAccount=True)
                users = [{user.Caption[decalage:]:user.status}
                         for user in wmi_UserAccount]
            except WmiModule.x_wmi as w:
                self.message_erreur += self.name + " erreur wmi: %s \n" % w.info
                if w.com_error is not None:
                    self.message_erreur += fix_str(w.com_error.strerror)
                # logger.error(self.name + ": " + str(w))
        return users

    def groupes_user(self, user):
        """retourne un dict contenant la liste des groupes de user """
        groupes = []
        decalage = len(self.name) + 1
        if self.etat == ALLUME:
            try:
                wmi = WmiModule.WMI(self.name)
                wmi_UserAccount = wmi.Win32_UserAccount(Name=user, LocalAccount=True)
                if wmi_UserAccount:
                    groupes = [groupe.Caption[decalage:]
                               for groupe in wmi_UserAccount[0].associators("Win32_GroupUser")]
            except WmiModule.x_wmi as w:
                self.message_erreur += "erreur wmi: %s \n" % w.info
                if w.com_error is not None:
                    self.message_erreur += fix_str(w.com_error.strerror)
                # logger.error(self.name + ": " + str(w))
        return groupes

    def ajouter_user(self, login, password, groupes):
        parametre_user = {
            'name': login,
            'password': password,
            'flags': win32netcon.UF_NORMAL_ACCOUNT | win32netcon.UF_SCRIPT,
            'priv': win32netcon.USER_PRIV_USER
        }
        try:
            win32net.NetUserAdd(self.name, 1, parametre_user)
        except pywintypes.error as error:
            log_erreur = "Erreur lors de la création du compte "\
                         + login + " : " + fix_str(error.strerror)
            self.message_erreur += log_erreur + "\n"
            # logger.error(log_erreur)

        for groupe in groupes:
            try:
                win32net.NetLocalGroupAddMembers(self.name, groupe, 3, [{'domainandname': login}])
            except pywintypes.error as error:
                log_erreur = "Erreur lors de l'attribution du groupe "\
                             + groupe + " : " + fix_str(error.strerror)
                self.message_erreur += log_erreur + "\n"
                # logger.error(self.name + ": " + log_erreur)
        return

    def supprimer_user(self, login):
        """ Supprime le compte login de la machine"""
        try:
            win32net.NetUserDel(self.name, login)
        except pywintypes.error as error:
            log_erreur = "Erreur lors de la suppression de l'utilisateur "\
                         + login + " : " + fix_str(error.strerror)
            self.message_erreur += log_erreur + "\n"
            # logger.error(self.name + ": " + log_erreur)
        return

    def chpwd_user(self, login, password):
        """Change le mot de passe du compte login """
        try:
            info = win32net.NetUserGetInfo(self.name, login, 3)
            info['password'] = password
            win32net.NetUserSetInfo(self.name, login, 3, info)
            info = win32net.NetUserGetInfo(self.name, login, 3)
        except pywintypes.error as error:
            log_erreur = "Erreur lors du changement de password de l'utilisateur "\
                         + login + " : " + fix_str(error.strerror)
            self.message_erreur += log_erreur + "\n"
            # logger.error(self.name + ": " + log_erreur)
        return

    def str_users(self):
        """ Retourne un string formatter avec colorama de la fonction lister_user()"""
        resultat = self.name + ': '
        if self.etat == ETEINT:
            resultat += "éteint"
            return resultat
        users = self.lister_users()

        for user in users:
            # list un dict recupere ses keys
            nom = list(user)[0]
            nom_coul = nom
            status = user[nom]
            if status != 'Degraded':
                nom_coul = Fore.LIGHTGREEN_EX + nom_coul + Fore.RESET
            if 'Administrateurs' in self.groupes_user(nom):
                nom_coul = Fore.LIGHTRED_EX + '*' + Fore.RESET + nom_coul
            resultat += nom_coul + ' '
        return resultat

    def str_user_groups(self, user):
        """Retourne un string formatter avec colorama de la fonction groupes_user() """
        groups = self.groupes_user(user)
        resultat = self.name + ': ' + user + '-> '
        if self.etat == ETEINT:
            resultat += "éteint"
            return resultat
        for group in groups:
            if group == 'Administrateurs':
                resultat += Fore.LIGHTRED_EX + group + Fore.RESET + ' '
            else:
                resultat += group + ' '
        return resultat


def main():
    pass

if __name__ == '__main__':
    main()
