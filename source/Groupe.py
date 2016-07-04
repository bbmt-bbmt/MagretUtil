#! python3
# coding: utf-8

import os
#import logging
# from logging.handlers import RotatingFileHandler
import concurrent.futures
import threading
import re
import difflib
import pythoncom
from Machine import Machine
from Machine import REMOTE_PATH
# from var_global import *
from colorama import Fore
import gc
import sys
import pathlib


# logger = logging.getLogger('MagretUtil.Salle')
#logger_info = logging.getLogger('Info')

# Constantes
ALLUME = 1
ETEINT = 0


class CounterThread:
    lock = threading.Lock()
    i = 0

    def __init__(self, upto=0):
        self.count = 0
        self.upto = upto or 1
        self.lock_count = threading.Lock()
        return

    @staticmethod
    def run_counter(word, counter):
        if counter is None:
            return
        counter.lock_count.acquire()
        counter.count = counter.count + 1
        percent = (counter.count * 100) // counter.upto
        sys.stdout.write('\r%s: %s%%' % (word, percent))
        counter.lock_count.release()


def score_str(str1, str2):
    score = difflib.SequenceMatcher(None, str1.strip(), str2.strip()).ratio() * 100
    return score


class Groupe:
    def __init__(self, name, names_machines, counter=True):

        def init_machine_thread(nom, counter=None):
            pythoncom.CoInitialize()
            try:
                m = Machine(nom)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return m

        self.name = name
        self.machines = []
        self.dict_machines = {}
        counter_thread = CounterThread(len(names_machines)) if counter else None
        self.machines = self._run_threads(init_machine_thread, *names_machines, counter=counter_thread)
        print()
        self.dict_machines = {machine.name: machine for machine in self.machines}
        self.machines.sort(key=lambda x: x.name)
        # self.notag()
        return

    def _run_threads(self, callback, *param, **kwargs):
        """fonction qui lance les threads de la fonction callback avec
        les paramètre *param"""
        result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
            future_to_machine = [executor.submit(callback, p, **kwargs)
                                 for p in param]
            for futur in concurrent.futures.as_completed(future_to_machine):
                if futur.exception() is not None:
                    raise futur.exception()
                result.append(futur.result())
        return result

    def add_user(self, login, password, groupes):
        def add_user_thread(machine, nom, password, groupes, counter=None):
            # important pour initialiser les trhead windows
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.ajouter_user(nom, password, groupes)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(add_user_thread, *self.machines, nom=login,
                          password=password, groupes=groupes, counter=counter_thread)
        print()
        return

    def del_user(self, login):
        def del_user_thread(machine, nom, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.supprimer_user(nom)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(del_user_thread, *self.machines, nom=login,
                          counter=counter_thread)
        print()
        return

    def chpwd_user(self, login, password):
        def chpwd_user_thread(machine, login, password, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.chpwd_user(login, password)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(chpwd_user_thread, *self.machines, login=login,
                          password=password, counter=counter_thread)
        print()
        return

    def update(self):
        list_names = list(self.dict_machines.keys())
        self.machines.clear()
        self.dict_machines.clear()
        gc.collect()
        self.__init__(self.name, list_names)
        return

    def run_remote_cmd(self, cmd, timeout=None, no_wait_output=False, counter=True):
        def machine_remote_cmd_thread(machine, cmd, timeout, no_wait_output, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.run_remote_cmd(cmd, timeout, no_wait_output)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines)) if counter else None
        self._run_threads(machine_remote_cmd_thread, *self.machines, cmd=cmd,
                          timeout=timeout, no_wait_output=no_wait_output,
                          counter=counter_thread)
        print()
        return

    def run_remote_file(self, file, param, timeout, no_wait_output=False):
        def machine_remote_file_thread(machine, file, param, timeout, no_wait_output, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.run_remote_file(file, param, timeout,
                                            no_wait_output)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(machine_remote_file_thread, *self.machines,
                          file=file, param=param, timeout=timeout,
                          no_wait_output=no_wait_output, counter=counter_thread)
        print()
        return

    def put(self, file_path, dir_path):
        def machine_put_thread(machine, file_path, dir_path, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.put(file_path, dir_path)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(machine_put_thread, *self.machines,
                          file_path=file_path, dir_path=dir_path, counter=counter_thread)
        print()

    def clean(self):
        def machine_clean_thread(machine, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    for name in machine.last_output_cmd.split():
                        if re.fullmatch(r'^todel[0-9]{1,4}[0-9|a-f]{32}$', name):
                            machine.run_remote_cmd('rd /s /q %s%s' % (REMOTE_PATH, name))
                    machine.vnc_close()
                    machine.last_output_cmd = ''
                CounterThread.run_counter(self.name, counter)
                #machine.registry.close_remote_registry()
            finally:
                pythoncom.CoUninitialize()
            return

        self.run_remote_cmd("dir /B c:\\ ")
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(machine_clean_thread, *self.machines,
                          counter=counter_thread)
        print()
        return

#    def notag(self):
#        def machine_notag_thread(machine):
#            pythoncom.CoInitialize()
#            try:
#                if machine.etat == ALLUME:
#                    for name in machine.last_output_cmd.split():
#                        if re.fullmatch(r'^tag_file_.*?$', name):
#                            machine.tag = True
#                    machine.last_output_cmd = ''
#            finally:
#                pythoncom.CoUninitialize()
#            return
#        self.run_remote_cmd("dir /B c:\\ ", counter=False)
#        self._run_threads(machine_notag_thread, *self.machines)
#        return

    def wol(self):
        for machine in self.machines:
            if machine.etat == ETEINT:
                machine.wol()
        return

    def shutdown(self):
        def machine_shutdown_thread(machine, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.shutdown()
                    machine.etat = ETEINT
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(machine_shutdown_thread, *self.machines, counter=counter_thread)
        print()
        return

    def uninstall(self, name):
        def uninstall_thread(machine, name_thread, counter=None):
            pythoncom.CoInitialize()
            try:
                if machine.etat == ALLUME:
                    machine.last_output_cmd = ''
                    machine.uninstall(name)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(uninstall_thread, *self.machines, name_thread=name,
                          counter=counter_thread)
        print()
        return

    def str_prog(self, filter=None):
        def str_prog_thread(machine, filter_thread, counter=None):
            pythoncom.CoInitialize()
            try:
                machine.last_output_cmd = ''
                machine.str_prog(filter)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return
        counter_thread = CounterThread(len(self.machines))
        self._run_threads(str_prog_thread, *self.machines, filter_thread=filter,
                          counter=counter_thread)
        print()
        return

    def str_logged(self):
        def str_logged_thread(machine, counter=None):
            pythoncom.CoInitialize()
            try:
                machine.last_output_cmd = ''
                str_resultat = machine.str_logged()
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET
        param = [machine for machine in self.machines]
        counter_thread = CounterThread(len(self.machines))
        resultat_threads = self._run_threads(str_logged_thread, *param,
                                             counter=counter_thread)
        resultat_threads = list(set(resultat_threads))
        try:
            resultat_threads.remove(None)
        except ValueError:
            # si None n'est pas dans la liste une exception est levée et on pass
            pass
        resultat_threads.sort()
        print()
        str_resultat += self.presentation(resultat_threads)
        return str_resultat

    def str_groupe(self):
        """fonction qui s'adapte en fonction du nombre de colonne de la
        console"""

        # récupère le nom du dernier fichier tag
        local_path = pathlib.Path('.')
        try:
            tag_file_name = list(local_path.glob("tag_file_*"))[0].name
        except (IndexError, AttributeError):
            tag_file_name = ''

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
                    if machine.tag == '':
                        resultat += Fore.LIGHTMAGENTA_EX + machine.name + Fore.RESET + ' '
                    elif machine.tag == tag_file_name:
                        resultat += Fore.LIGHTGREEN_EX + machine.name + Fore.RESET + ' '
                    else:
                        resultat += Fore.LIGHTYELLOW_EX + machine.name + Fore.RESET + ' '
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
        # str_template = "{:<%i}" % max_len
        for liste in sous_listes_str:
            for s in liste:
                pad = max_len - len(re.sub('\x1b.*?m', '', s))
                str_resultat += s + (pad + 4) * ' '
            str_resultat += '\n'
        return str_resultat

    def str_users(self):
        def str_users_thread(machine, counter=None):
            pythoncom.CoInitialize()
            try:
                machine.last_output_cmd = ''
                str_resultat = machine.str_users()
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET
        param = [machine for machine in self.machines]
        counter_thread = CounterThread(len(self.machines))
        resultat_threads = self._run_threads(str_users_thread, *param,
                                             counter=counter_thread)
        resultat_threads.sort()
        print()
        str_resultat += self.presentation(resultat_threads)
        return str_resultat

    def str_user_groups(self, user):
        def str_user_groups_thread(machine, user, counter=None):
            pythoncom.CoInitialize()
            try:
                machine.last_output_cmd = ''
                str_resultat = machine.str_user_groups(user)
                CounterThread.run_counter(self.name, counter)
            finally:
                pythoncom.CoUninitialize()
            return str_resultat

        str_resultat = ""
        resultat_threads = []
        str_resultat += Fore.LIGHTCYAN_EX + self.name + '\n' + Fore.RESET

        counter_thread = CounterThread(len(self.machines))
        resultat_threads = self._run_threads(str_user_groups_thread,
                                             *self.machines, user=user,
                                             counter=counter_thread)
        resultat_threads.sort()
        print()
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
