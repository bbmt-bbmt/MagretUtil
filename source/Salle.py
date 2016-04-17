#! python3
# coding: utf-8

import os
import logging
# from logging.handlers import RotatingFileHandler
import re
import difflib
import pythoncom
from Machine import Machine
from Groupe import Groupe
from var_global import *
from colorama import Fore
import gc


# logger = logging.getLogger('MagretUtil.Salle')
logger_info = logging.getLogger('Info')

# Constantes
ALLUME = 1
ETEINT = 0


def score_str(str1, str2):
    score = difflib.SequenceMatcher(None, str1, str2).ratio()*100
    return score


class Salle(Groupe):
    def __init__(self, name, nbre):

        def init_machine_thread(nom):
            pythoncom.CoInitialize()
            try:
                m = Machine(nom)
            finally:
                pythoncom.CoUninitialize()
            return m

        self.nbre = nbre
        num = len(str(self.nbre)) if nbre >= 10 else 2
        str_template = '%s-P%0--i'.replace('--', str(num))
        noms_machines = [str_template % (name, i) for i in range(1, nbre + 1)]
        super().__init__(name, noms_machines)
        return

    def update(self):
        def machine_update_thread(machine):
            pythoncom.CoInitialize()
            try:
                machine.update_etat()
            finally:
                pythoncom.CoUninitialize()
            return

        self.machines.clear()
        self.dict_machines.clear()
        gc.collect()
        self.__init__(self.name, self.nbre)
        return

    def str_groupe(self):
        """fonction qui s'adapte en fonction du nombre de colonne de la
        console"""
        columns_term = os.get_terminal_size().columns
        lignes = [Fore.LIGHTCYAN_EX + self.name + Fore.RESET, ]
        resultat = ''

        for machine in self.machines:
            num_machine = self.machines.index(machine) + 1
            # on coupe la sortie en fonction du nombre de colonne et on ne compte pas les caractère spéciaux
            if len(re.sub('\x1b.*?m', '', resultat)) + len(str(num_machine)) >= columns_term:
                lignes.append(resultat.strip())
                resultat = ''
            # formatage couleur de la sortie
            if machine.message_erreur == '':
                if machine.etat == ETEINT:
                    resultat += str(num_machine) + ' '
                if machine.etat == ALLUME:
                    resultat += Fore.LIGHTGREEN_EX + str(num_machine) + Fore.RESET + ' '
            else:
                resultat += Fore.LIGHTRED_EX + str(num_machine) + Fore.RESET + ' '

        lignes.append(resultat.strip())
        resultat = "\n".join(lignes)
        return resultat


def main():
    pass

if __name__ == '__main__':
    main()
