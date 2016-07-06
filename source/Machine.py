#! python3
# coding: utf-8

import winreg
import socket
import struct
import win32net
import win32netcon
import pywintypes
import wmi as WmiModule
import re
import os
import subprocess
import time
# import pathlib
# import logging
import Psexec

from colorama import Fore

from var_global import fix_str

# logger = logging.getLogger("MagretUtil.Machine")

# Constantes
ALLUME = 1
ETEINT = 0
REMOTE_PATH = 'c:\\'
SUB_KEY_UNINSTALL = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
SUB_KEY_WOW_UNINSTALL = "SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"


def walk_reg_prog(connect, sub_key):
    result_dict = {}
    winreg_sub_key = winreg.OpenKey(connect, sub_key,
                                    access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
    try:    
        i = 0
        while True:
            str_key = winreg.EnumKey(winreg_sub_key, i)
            key_prog = winreg.OpenKey(connect,
                                      sub_key + "\\" + str_key,
                                      access=winreg.KEY_READ | winreg.KEY_WOW64_64KEY)
            try:
                j = 0
                name_prog = None
                uninstall = None
                while True:
                    name, value, id_number = winreg.EnumValue(key_prog, j)
                    if name == "DisplayName":
                        name_prog = value
                    if name == "UninstallString":
                        uninstall = value
                    if name_prog and uninstall:
                        break
                    j = j + 1
                if name_prog and uninstall:
                    result_dict[name_prog] = uninstall
            except OSError:
                pass
            i = i + 1
    except (OSError,FileNotFoundError):
        pass
    return result_dict


class Machine:
    """Class qui représente un ordi et son état
(allumé-éteint-erreur-ip-mac) """

    def __init__(self, name):
        self.name = name
        self.etat = ETEINT
        self.ip = None
        self.mac = None
        self.tag = ''
        self._vnc_uid = None
        self.prog32 = None
        self.prog64 = None
        self.message_erreur = ""
        self.last_output_cmd = ""
        self.update_etat()
        # print(walk_reg_prog2(self.name, 'HKLM\\' + SUB_KEY32, '32'))
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
                self.last_output_cmd = fix_str(output_data)
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

    def _run_gui_file(self, local_file, login):
        """Permet de lancer un executable de la machine local avec
        les droits de l'utilisateur connecté et ainsi pouvoir interagir
        avec le bureau
        """
        # j'utilise schtask plutot que du wmi car l'implémentation avec wmi
        # repose sur la commande déprécié at
        subprocess.call(['schtasks', '/create', '/tn', 'todel', '/tr', local_file, '/s', self.name, '/ru', login, '/sc', 'ONSTART', '/it', '/f'], stdout=subprocess.DEVNULL)
        subprocess.call(['schtasks', '/run', '/tn', 'todel', '/s', self.name, '/i'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        subprocess.call(['schtasks', '/delete', '/tn', 'todel', '/s', self.name, '/f'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        return

    def logged(self):
        """ Retourne le login de l'utilisateur connecté sur la machine
        pour pouvoir après le donner à run_gui_file
        """
        try:
            wmi = WmiModule.WMI(self.name)
            user_logged = wmi.Win32_ComputerSystem()[0].UserName
        except WmiModule.x_wmi as w:
                self.message_erreur += self.name + " erreur wmi: %s \n" % w.info
                if w.com_error is not None:
                    self.message_erreur += fix_str(w.com_error.strerror)
                return None
        return user_logged

    def vnc_open(self, computer_name):
        """ lance le serveur sur la machine après avoir copié tous les
        fichiers nécessaire
        """
        if self.etat == ETEINT:
            return
        self.vnc_close()
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
            self._vnc_uid = _psexec._get_uid()
            remote_directory = os.path.join(_psexec.remote_path, self._vnc_uid)
            vnc_file = ['vnc\\winvnc.exe', 'vnc\\UltraVNC.ini', 'vnc\\vnchooks.dll']

            for file in vnc_file:
                _psexec._net_copy(file, remote_directory)

            cmd_run = os.path.join(remote_directory, 'winvnc.exe')
            cmd_connect = os.path.join(remote_directory,
                                       'winvnc.exe -connect ' + computer_name)

            login = self.logged()
            if login is not None:
                self._run_gui_file(cmd_run, login)
                self._run_gui_file(cmd_connect, login)
            else:
                print('Aucun utilisateur connecté')
                self.vnc_close()
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
        except FileNotFoundError as f:
            self.message_erreur += "Le fichier %s n'existe pas" % f.filename
        finally:
            _psexec = None
        return

    def vnc_close(self):
        """ Kill le server vnc de la machine
        """
        if self.etat == ETEINT:
            return
        try:
            subprocess.call(["taskkill", "/F", "/IM", "winvnc.exe", '/s', self.name],
                            stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
        finally:
            self._vnc_uid = None
        return

    def put(self, file_path, dir_path):
        try:
            _psexec = Psexec.PsExec(self.name, REMOTE_PATH)
            _psexec._net_copy(file_path, dir_path)
        except FileExistsError:
            self.message_erreur += "le fichier existe déja"
        except PermissionError:
            self.message_erreur += "Vous n'avez pas les droits administrateur\n"
        except WmiModule.x_wmi as w:
            self.message_erreur += "erreur wmi: %s \n" % w.info
            if w.com_error is not None:
                self.message_erreur += fix_str(w.com_error.strerror)
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
            # pour gérer une erreur d'import qui peut arriver dans le module wmi ????
            except ImportError:
                self.message_erreur += self.name + " erreur wmi"

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

    def open_remote_registry(self):
        if self.etat == ETEINT:
            return
        try:
            wmi_connect = WmiModule.WMI(self.name)
            remote_registry = wmi_connect.Win32_Service(name="RemoteRegistry")[0]
            remote_registry.StartService()
        except WmiModule.x_wmi as w:
            self.message_erreur += self.name + " erreur wmi: %s \n" % w.info
            if w.com_error is not None:
                self.message_erreur += fix_str(w.com_error.strerror)
        return

    def init_tag(self):
        if self.etat == ETEINT:
            return
        self.run_remote_cmd("dir /B c:\\tag_file_*")
        name_tag_file = self.last_output_cmd
        try:
            name_tag_file = re.search('tag_file_[\\d]*', name_tag_file).group(0)
        except (IndexError, AttributeError):
            name_tag_file = ''
        self.tag = name_tag_file
        return

    def update_etat(self):
        """met à jour la machine :
efface les erreurs, met à jour l'état, l'ip """
        self.message_erreur = ''
        self.last_output_cmd = ''
        self.prog32 = {}
        self.prog64 = {}
        self.ping()
        self.init_mac()
        self.init_tag()
        self.open_remote_registry()
        return

    def connect_registry(self):
        #try:
        #    wmi_connect = WmiModule.WMI(self.name)
        #except WmiModule.x_wmi as w:
        #    self.message_erreur += self.name + " erreur wmi: %s \n" % w.info
        #    if w.com_error is not None:
        #        self.message_erreur += fix_str(w.com_error.strerror)
        #    return
        timeout = time.time() + 3
        remote_running = False
        HKLM = None
        # boucle avec timout pour être sur que l'accès à distance est bon
        while time.time() < timeout:
            try:
                HKLM = winreg.ConnectRegistry(self.name, winreg.HKEY_LOCAL_MACHINE)
                remote_running = True
                break
            except Exception:
                continue
                #break
            #remote_registry = wmi_connect.Win32_Service(name="RemoteRegistry")[0]
            #if remote_registry.State == "Running":
            #    remote_running = True
            #    break
        if remote_running is False:
            self.message_erreur += "Le registre n'est pas accessible à distance"
        return HKLM

    def list_prog(self, filter):
        HKLM = self.connect_registry()
        win64 = True
        result_prog32 = {}
        result_prog64 = {}
        if HKLM is None:
            return ()
        try:
            result_prog32 = walk_reg_prog(HKLM, SUB_KEY_WOW_UNINSTALL)
        except FileNotFoundError:
            result_prog32 = walk_reg_prog(HKLM, SUB_KEY_UNINSTALL)
            win64 = False

        if filter is not None:
            result_prog32 = {key: value for key, value in result_prog32.items()
                             if filter.lower() in key.lower()}
        if win64 is True:
            result_prog64 = walk_reg_prog(HKLM, SUB_KEY_UNINSTALL)
            if filter is not None:
                result_prog64 = {key: value for key, value in result_prog64.items()
                                 if filter.lower() in key.lower()}
        return (result_prog32, result_prog64)

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
                win32net.NetLocalGroupAddMembers(self.name, groupe, 3,
                                                 [{'domainandname': login}])
            except pywintypes.error as error:
                log_erreur = "Erreur lors de l'attribution du groupe "\
                             + groupe + " : " + fix_str(error.strerror)
                self.message_erreur += log_erreur + "\n"
        return

    def supprimer_user(self, login):
        """ Supprime le compte login de la machine"""
        try:
            win32net.NetUserDel(self.name, login)
        except pywintypes.error as error:
            log_erreur = "Erreur lors de la suppression de l'utilisateur "\
                         + login + " : " + fix_str(error.strerror)
            self.message_erreur += log_erreur + "\n"
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
        return

    def uninstall(self, name):
        prog_3264 = self.list_prog(name)
        # si la liste est vide, il n'y a rien à faire
        if not prog_3264:
            return
        prog = prog_3264[0].copy()
        prog.update(prog_3264[1])
        if len(prog) != 1 or not prog:
            self.message_erreur += "erreur dans le nom du programme à desinstaller\n"
            self.message_erreur += "le nom peut correspondre à plusieur programme ou le nom n'existe pas\n"
            return
        for prog_name, cmd_uninstall in prog.items():
            pass
        if "msiexec" not in cmd_uninstall.lower():
            self.last_output_cmd = cmd_uninstall
        else:
            try:
                uid_prog = re.findall(r"\{[a-zA-Z0-9-]*\}", cmd_uninstall)[0]
            except IndexError:
                self.message_erreur = "impossible de desinstaller le logiciel"
            self.run_remote_cmd("msiexec.exe /qn /x " + uid_prog, no_wait_output=True)
        return

    def str_prog(self, filter=None):
        if self.etat == ETEINT:
            return None
        prog = self .list_prog(filter)
        if not prog:
            return
        self.last_output_cmd = "PROGRAMMES 32b:\n"
        prog32 = prog[0]
        prog64 = prog[1]
        # les variables suivantes servent à afficher les résultats du dict dans l'ordre
        lprog32 = list(prog32)
        lprog32.sort(key=lambda x: x.lower())
        lprog64 = list(prog64)
        lprog64.sort(key=lambda x: x.lower())
        for prog in lprog32:
            if "msiexec" in prog32[prog].lower():
                self.last_output_cmd += Fore.LIGHTGREEN_EX + prog + Fore.RESET + "\n"
            else:
                self.last_output_cmd += Fore.LIGHTRED_EX + prog + Fore.RESET + "\n"

        self.last_output_cmd += "PROGRAMMES 64b:\n"
        for prog in lprog64:
            if "msiexec" in prog64[prog].lower():
                self.last_output_cmd += Fore.LIGHTGREEN_EX + prog + Fore.RESET + "\n"
            else:
                self.last_output_cmd += Fore.LIGHTRED_EX + prog + Fore.RESET + "\n"
        # je n'utilise pas fix_str içi car je suis tombé un jour sur un logiciel avec
        # des caractère chinois (mblock)
        # c'est le groupe qui utilisera encode decode avec replace ou ignore
        return self.last_output_cmd

    def str_logged(self):
        if self.etat == ETEINT:
            return None
        resultat = self.name + ': '
        user_logged = self.logged()
        if user_logged is not None:
            resultat += Fore.LIGHTGREEN_EX + user_logged + Fore.RESET
        else:
            resultat = None
        return resultat

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
    import colorama
    colorama.init()
    m = Machine('DESKTOP-P01')
    #print(m.str_prog("scratch"))
    #m.uninstall("scratch")
    #print(m.str_prog("scratch"))

    # print(m.last_output_cmd)
    pass

if __name__ == '__main__':
    main()
