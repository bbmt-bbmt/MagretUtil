#! python3
# coding: utf-8

import os
import logging
# from logging.handlers import RotatingFileHandler
import concurrent.futures
import re
import difflib
import pythoncom
from Machine import Machine
from Machine import REMOTE_PATH
# from var_global import *
from colorama import Fore
import gc


# logger = logging.getLogger('MagretUtil.Salle')
logger_info = logging.getLogger('Info')

# Constantes
ALLUME = 1
ETEINT = 0


def score_str(str1, str2):
    score = difflib.SequenceMatcher(None, str1, str2).ratio() * 100
    return score


class Groupe:
    def __init__(self, name, names_machines):

        def init_machine_thread(nom):
            pythoncom.CoInitialize()
            try:
                m = Machine(nom)
            finally:
                pythoncom.CoUninitialize()
            return m

        self.name = name
        self.machines = []
        self.dict_machines = {}

        self.machines = self._run_threads(init_machine_thread, *names_machines)
        self.dict_machines = {machine.name: machine for machine in self.machines}
        self.machines.sort(key=lambda x: x.name)
        logger_info.info("groupe %s créé" % self.name)
        return

    def _run_threads(self, callback, *param, **kwargs):
        """fonction qui lance les threads de la fonction callback avec
        les paramètre *param"""
        result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            future_to_machine = [executor.submit(callback, p, **kwargs)
                                 for p in param]
            for futur in concurrent.futures.as_completed(future_to_machine):
                if futur.exception() is not None:
                    raise futur.exception()
                result.append(futur.result())
        return result

    def add_user(self, login, password, groupes):
        def add_user_thread(machine, nom, password, groupes):
            # important pour initialiser les trhead windows
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.ajouter_user(nom, password, groupes)
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(add_user_thread, *self.machines, nom=login,
                          password=password, groupes=groupes)

        logger_info.info("%s OK" % self.name)
        return

    def del_user(self, login):
        def del_user_thread(machine, nom):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.supprimer_user(nom)
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(del_user_thread, *self.machines, nom=login)
        logger_info.info("%s OK" % self.name)
        return

    def chpwd_user(self, login, password):
        def chpwd_user_thread(machine, login, password):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.chpwd_user(login, password)
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(chpwd_user_thread, *self.machines, login=login,
                          password=password)
        logger_info.info("%s OK" % self.name)
        return

    def update(self):
        list_names = list(self.dict_machines.keys())
        self.machines.clear()
        self.dict_machines.clear()
        gc.collect()
        self.__init__(self.name, list_names)
        return

    def run_remote_cmd(self, cmd, timeout=None, no_wait_output=False):
        def machine_remote_cmd_thread(machine, cmd, timeout, no_wait_output):
            pythoncom.CoInitialize()
            if machine.etat == ALLUME:
                machine.run_remote_cmd(cmd, timeout, no_wait_output)
            pythoncom.CoUninitialize()
            return

        self._run_threads(machine_remote_cmd_thread, *self.machines, cmd=cmd,
                          timeout=timeout, no_wait_output=no_wait_output)
        logger_info.info("%s OK" % self.name)
        return

    def run_remote_file(self, file, param, timeout, no_wait_output=False):
        def machine_remote_file_thread(machine, file, param, timeout, no_wait_output):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.run_remote_file(file, param, timeout,
                                            no_wait_output)
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(machine_remote_file_thread, *self.machines,
                          file=file, param=param, timeout=timeout,
                          no_wait_output=no_wait_output)
        logger_info.info("%s OK" % self.name)
        return

    def put(self, file_path, dir_path):
        def machine_put_thread(machine, file_path, dir_path):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.put(file_path, dir_path)
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(machine_put_thread, *self.machines,
                          file_path=file_path, dir_path=dir_path)
        logger_info.info("%s OK" % self.name)

    def clean(self):
        def machine_clean_thread(machine):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    for name in machine.last_output_cmd.split():
                        if re.fullmatch(r'^todel[0-9]{1,4}[0-9|a-f]{32}$', name):
                            machine.run_remote_cmd('rd /s /q %s%s' % (REMOTE_PATH, name))
            finally:
                pythoncom.CoUninitialize()
            return

        self.run_remote_cmd("dir /B c:\ ")
        self._run_threads(machine_clean_thread, *self.machines)
        logger_info.info("%s OK" % self.name)
        return

    def wol(self):
        for machine in self.machines:
            if machine.etat == ETEINT:
                machine.wol()
        return

    def shutdown(self):
        def machine_shutdown_thread(machine):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.shutdown()
                    machine.etat = ETEINT
            finally:
                pythoncom.CoUninitialize()
            return

        self._run_threads(machine_shutdown_thread, *self.machines)
        logger_info.info("%s OK" % self.name)
        return

    def str_logged(self):
        def str_logged_thread(machine):
            pythoncom.CoInitialize()
            try:
                str_resultat = machine.str_logged()
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET
        param = [machine for machine in self.machines]
        resultat_threads = self._run_threads(str_logged_thread, *param)
        resultat_threads = list(set(resultat_threads))
        try:
            resultat_threads.remove(None)
        except ValueError:
            # si None n'est pas dans la liste une exception est levée et on pass
            pass
        resultat_threads.sort()
        logger_info.info("%s OK" % self.name)
        str_resultat += self.presentation(resultat_threads)
        return str_resultat

    def str_groupe(self):
        """fonction qui s'adapte en fonction du nombre de colonne de la
        console"""
        columns_term = os.get_terminal_size().columns
        lignes = [Fore.LIGHTCYAN_EX + self.name + Fore.RESET, ]
        resultat = ''

        for machine in self.machines:
            # on coupe la sortie en fonction du nombre de colonne
            # et on ne compte pas les caractère spéciaux
            if len(re.sub('\x1b.*?m', '', resultat)) + len(machine.name) >= columns_term:
                lignes.append(resultat.strip())
                resultat = ''
            # formatage couleur de la sortie
            if machine.message_erreur == '':
                if machine.etat == ETEINT:
                    resultat += machine.name + ' '
                if machine.etat == ALLUME:
                    resultat += Fore.LIGHTGREEN_EX + machine.name + Fore.RESET + ' '
            else:
                resultat += Fore.LIGHTRED_EX + machine.name + Fore.RESET + ' '

        lignes.append(resultat.strip())
        resultat = "\n".join(lignes)
        return resultat

    def presentation(self, liste_str):
        """utilisé par str_users et str_user_group pour adapter la sortie en
fonction du nombre de colonne de la console """
        columns_term = os.get_terminal_size().columns
        str_resultat = ""
        # on repere la plus longue sortie qui servira de reference
        max_len = len(max([re.sub('\x1b.*?m', '', s) for s in liste_str], key=len, default=''))
        # nbre_col-> compte combien de sortie on va mettre sur une meme ligne
        # avec un espacement minimum de 4
        nbre_col = columns_term // (max_len + 4)
        # on decooupe, chaque element de sous_liste_str correspond à une ligne
        sous_listes_str = [liste_str[i:i + nbre_col]
                           for i in range(0, len(liste_str), nbre_col)]
        str_template = "{:<%i}" % max_len
        for liste in sous_listes_str:
            str_resultat += "    ".join([str_template.format(s) for s in liste]) + '\n'
        return str_resultat

    def str_users(self):
        def str_users_thread(machine):
            pythoncom.CoInitialize()
            try:
                str_resultat = machine.str_users()
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET
        param = [machine for machine in self.machines]
        resultat_threads = self._run_threads(str_users_thread, *param)
        resultat_threads.sort()
        logger_info.info("%s OK" % self.name)
        str_resultat += self.presentation(resultat_threads)
        return str_resultat

    def str_user_groups(self, user):
        def str_user_groups_thread(machine, user):
            pythoncom.CoInitialize()
            try:
                str_resultat = machine.str_user_groups(user)
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET

        resultat_threads = self._run_threads(str_user_groups_thread, *self.machines, user=user)
        resultat_threads.sort()
        logger_info.info("%s OK" % self.name)
        str_resultat += self.presentation(resultat_threads)
        return str_resultat

    def str_erreurs(self):
        str_resultat = Fore.LIGHTCYAN_EX + self.name + Fore.RESET + '\n'
        for machine in self.machines:
            if machine.message_erreur != '':
                str_resultat += Fore.LIGHTRED_EX + machine.name + ': '\
                    + Fore.RESET + machine.message_erreur + '\n'
        return str_resultat

    def str_cmp(self, str_ref, seuil):
        str_resultat = Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET
        for machine in self.machines:
            score = score_str(machine.last_output_cmd, str_ref)
            if machine.etat == ETEINT:
                str_resultat += machine.name + ' '
            if machine.etat == ALLUME:
                if score < seuil:
                    str_resultat += Fore.LIGHTRED_EX + machine.name + ' ' + Fore.RESET
                else:
                    str_resultat += Fore.LIGHTGREEN_EX + machine.name + ' ' + Fore.RESET
        return str_resultat

    def __iter__(self):
        return iter(self.machines)


def main():
    pass

if __name__ == '__main__':
    main()
