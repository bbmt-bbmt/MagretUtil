#! python3
# coding: utf-8

import os
import sys
import configparser
import logging
import re
import gc
import traceback
import getpass


from logging import FileHandler
import colorama
colorama.init()


logger = logging.getLogger('MagretUtil')
logger_info = logging.getLogger('Info')
logger.setLevel(logging.WARNING)
logger_info.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s :: %(name)s :: %(levelname)s\n' + '=' * 100 + '\n%(message)s' + '=' * 100)
# file_handler = RotatingFileHandler('error.log', mode='w', 1000000, 1)
file_handler = FileHandler('error.log', 'w')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logger_info.addHandler(stream_handler)

from Machine import Machine
from Groupe import Groupe
from Salle import Salle
import commandes
from var_global import *
import Privilege


def _protect_quotes(text):
    lst = text.split('"')
    for i, item in enumerate(lst):
        if i % 2:
            lst[i] = re.sub(r'\s', "::", item)
    return '"'.join(lst)


def _remove_protect_char(lst_str):
    return [re.sub(r'::', ' ', s) for s in lst_str]


def lire_fichier_ini(fichier):
    """ Retourne les variables necessaire pour le fonctionnement retourne un
    dictionnaire {nom_groupe:nbre_poste}"""
    try:
        config = configparser.ConfigParser()
        config.read(fichier, encoding="utf-8-sig")
    except configparser.Error as e:
        print("erreur lors de l'initialisation du fichier ini : ")
        raise SystemExit

    groupes_dict = {}
    groupes_dict['GroupesMagret'] = {}
    groupes_dict['Groupes'] = {}
    domaine = {}
    try:
        for groupe in config['GroupesMagret']:
            num_poste = config['GroupesMagret'][groupe].split('-')[1]
            nbre_poste = int(num_poste[1:])
            if nbre_poste != 0:
                groupes_dict['GroupesMagret'][groupe.upper()] = nbre_poste

        for groupe in config['Groupes']:
            groupes_dict['Groupes'][groupe.upper()] = config['Groupes'][groupe]
    except ValueError:
        pass
    except Exception as e:
        print('Erreur de lecture du fichier config')
        logger.critical(e)
        raise SystemExit()

    domaine['name'] = config.get('Domaine', 'domaine', fallback=None)
    domaine['login'] = config.get('Domaine', 'login', fallback=None)
    return groupes_dict, domaine


def erreur_final(e_type, e_value, e_tb):
    print('erreur critique, voir le fichier de log')
    logger.critical(''.join(traceback.format_exception(e_type, e_value, e_tb)))
    # pdb.post_mortem(e_tb)
    return


def init_groupes(ini_groupes):
    global groupes, selected_groupes, machines_dict

    for ini_salle, nbre in ini_groupes['GroupesMagret'].items():
        groupes.append(Salle(ini_salle, nbre))
    for ini_groupe, list_machine in ini_groupes['Groupes'].items():
        list_machine = list_machine.split(',')
        groupes.append(Groupe(ini_groupe, list_machine))
    groupes.sort(key=lambda x: x.name)

    machines_dict.update({machine.name: machine for g in groupes for machine in g})
    return


def main():
    global domaine
    sys.excepthook = erreur_final

    ini_groupes, dom = lire_fichier_ini('conf.ini')
    # on initialise la variable domaine qui contient le login administrateur
    # du domaine
    domaine.update(dom)

    # Si le login du fichier config est différent que celui avec lequel
    # on est connecté, on lance la procédure délévation de privilège
    if domaine['login'] is not None and getpass.getuser() != domaine['login']:
        commandes.password(['uac'])

    # Si une demande de bypasser l'uac est demandé, on lance la procédure
    if sys.argv[1:] and sys.argv[1] == "pass_uac":
        Privilege.pass_uac()
        raise SystemExit()

    logger_info.info('Initialisation des salles :')
    init_groupes(ini_groupes)

    # efface l'écran
    print('\x1b[2J', end='')

    while True:
        param = input('>>>')
        param = _protect_quotes(param)
        param = param.strip()
        param = param.split(' ')
        param = _remove_protect_char(param)
        cmd = param[0]
        param.remove(cmd)

        cmd = cmd.lower()
        cmd_funct = getattr(commandes, cmd, commandes.help)
        try:
            cmd_funct(param)

            # nettoie une partie de ceux qui a été laissé par les threads
            # de la dernière commande
            # contrôle l'augmentation de la mémoire pour le multithread
            gc.collect()
            # print('com-ref: ', pythoncom._GetInterfaceCount())
            print('-' * (os.get_terminal_size().columns - 1))
        except Warning:
            cmd_funct(['help'])
            gc.collect()
            # print(pythoncom._GetInterfaceCount())
            print('-' * (os.get_terminal_size().columns - 1))

if __name__ == '__main__':
    main()
